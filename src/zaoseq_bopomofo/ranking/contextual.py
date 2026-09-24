"""把候選排序轉成 closed-choice 決策的通用 ranker，與具體模型無關。"""

from __future__ import annotations

import concurrent.futures
import math
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from dataclasses import replace

from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.decoding.family import VariantTable, group_families
from zaoseq_bopomofo.ranking.base import (
    FallbackInfo,
    FallbackReason,
    RankingContext,
    RankingResult,
    RankingStatus,
    baseline_ranked,
    elapsed_ms,
    order_by_scores,
    validate_candidates,
)
from zaoseq_bopomofo.ranking.signal import ContextSignal


@dataclass(frozen=True)
class ChoiceOption:
    candidate_id: str
    text: str


@dataclass(frozen=True)
class ChoiceRequest:
    left_context: str
    readings: tuple[str, ...]
    options: tuple[ChoiceOption, ...]


@dataclass(frozen=True)
class ChoiceDistribution:
    """backend 的原始輸出，尚未驗證；`probabilities` 以 candidate_id 為 key。"""

    model_name: str
    probabilities: Mapping[str, float]
    confidence: float | None
    signal: ContextSignal | None = None


class BackendUnavailableError(RuntimeError):
    """模型未安裝、未載入或正忙；與模型推論本身出錯分開統計。"""


class UnknownCandidateError(RuntimeError):
    """模型回答了請求選項以外的東西。"""


class InvalidBackendResponseError(RuntimeError):
    """backend 自己在聚合前就發現模型輸出不合法（例如 pairwise 機率為 NaN 或題數不符）。"""


@runtime_checkable
class ContextualBackend(Protocol):
    @property
    def model_name(self) -> str: ...

    def decide(self, request: ChoiceRequest) -> ChoiceDistribution: ...


class _InvalidResponse(Exception):
    def __init__(self, reason: FallbackReason, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason


class ContextualRanker:
    """以 backend 取得 baseline 前 `top_k` 名的完整機率分佈並排序；任何失敗都 fallback 到 baseline。

    - `top_k`：Laya 的 choice head 在選項多時每個選項分到的 token 會急遽變少（官方建議 < 20），
      所以只送前 k 名；其餘維持 baseline 順序接在後面，模型無法把它們往前提。
    - `max_context_chars`：只保留最靠近游標的前文，也避免長前文吃掉選項的 token 預算。
    - `probability_tolerance`：Laya 把機率四捨五入到小數 4 位，12 個選項最多累積約 6e-4 誤差。
    模型輸出不合法時一律 fallback，不自行 renormalize，否則會掩蓋 backend 或協定的問題。
    """

    def __init__(
        self,
        backend: ContextualBackend,
        name: str = "contextual",
        timeout_s: float = 2.0,
        top_k: int = 12,
        max_context_chars: int = 64,
        probability_tolerance: float = 1e-3,
        variants: VariantTable | None = None,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s 必須 > 0")
        if top_k < 2:
            raise ValueError("top_k 至少為 2")
        if max_context_chars < 0:
            raise ValueError("max_context_chars 不可為負")
        self._backend = backend
        self._name = name
        self._timeout_s = timeout_s
        self._top_k = top_k
        self._max_context_chars = max_context_chars
        self._tolerance = probability_tolerance
        self._variants = variants
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix=name)
        # Python 無法中止執行中的 thread；記下已 timeout 但還在跑的推論，避免新請求排在它後面。
        self._stale: concurrent.futures.Future[ChoiceDistribution] | None = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str | None:
        return self._backend.model_name

    def rank(self, context: RankingContext, candidates: Sequence[Candidate]) -> RankingResult:
        started = time.perf_counter()
        validate_candidates(candidates)
        if not candidates:
            return RankingResult(self._name, self.model_name, RankingStatus.EMPTY, (), elapsed_ms(started))
        if len(candidates) == 1:
            # 單一候選沒有決策空間，不呼叫模型；contextual_probability 保持 None 表示未評估。
            return RankingResult(
                ranker=self._name,
                model=self.model_name,
                status=RankingStatus.OK,
                candidates=baseline_ranked(candidates),
                latency_ms=elapsed_ms(started),
                notes=("single_candidate",),
            )

        # 視窗以 family 為單位：同族的寫法變體不會同時佔用 top-k，只由代表進入模型。
        families = group_families(candidates, self._variants)
        window_families = families[: self._top_k]
        window = [f.representative for f in window_families]
        if len(window) == 1:
            return RankingResult(
                ranker=self._name,
                model=self.model_name,
                status=RankingStatus.OK,
                candidates=baseline_ranked(candidates),
                latency_ms=elapsed_ms(started),
                notes=("single_family",),
            )
        request = ChoiceRequest(
            left_context=context.left_context[-self._max_context_chars :] if self._max_context_chars else "",
            readings=context.readings,
            options=tuple(ChoiceOption(c.candidate_id, c.text) for c in window),
        )
        model_started = time.perf_counter()
        try:
            distribution = self._call(request)
        except (concurrent.futures.TimeoutError, TimeoutError):
            return self._fallback(candidates, started, FallbackReason.TIMEOUT, f"超過 {self._timeout_s:.2f}s", model_started)
        except BackendUnavailableError as exc:
            return self._fallback(candidates, started, FallbackReason.UNAVAILABLE, str(exc), model_started)
        except UnknownCandidateError as exc:
            return self._fallback(candidates, started, FallbackReason.UNKNOWN_CANDIDATE, str(exc), model_started)
        except InvalidBackendResponseError as exc:
            return self._fallback(candidates, started, FallbackReason.INVALID_PROBABILITY, str(exc), model_started)
        except Exception as exc:  # noqa: BLE001 - backend 的任何例外都必須轉成 fallback
            detail = f"{type(exc).__name__}: {exc}"
            return self._fallback(candidates, started, FallbackReason.BACKEND_ERROR, detail, model_started)
        model_ms = elapsed_ms(model_started)

        try:
            probabilities = self._validate(distribution, [o.candidate_id for o in request.options])
            confidence = _validate_unit_interval(distribution.confidence, "confidence")
        except _InvalidResponse as invalid:
            return self._fallback(candidates, started, invalid.reason, str(invalid), model_started, model_ms)

        notes: tuple[str, ...] = ()
        outside = len(candidates) - sum(len(f.members) for f in window_families)
        if outside:
            notes = (f"top_k={len(window)} families: 其餘 {outside} 個候選維持 baseline 順序",)
        family_scores: dict[str, float] = {}
        representatives: set[str] = set()
        for family in window_families:
            probability = probabilities[family.representative.candidate_id]
            representatives.add(family.representative.candidate_id)
            for member in family.members:
                family_scores[member.candidate_id] = probability
        ranked = tuple(
            replace(rc, family_representative=rc.candidate.candidate_id in representatives or rc.contextual_probability is None)
            for rc in order_by_scores(candidates, family_scores, family_scores)
        )
        return RankingResult(
            ranker=self._name,
            model=distribution.model_name,
            status=RankingStatus.OK,
            candidates=ranked,
            latency_ms=elapsed_ms(started),
            confidence=confidence,
            notes=notes,
            model_latency_ms=model_ms,
            signal=distribution.signal,
        )

    @property
    def top_k(self) -> int:
        return self._top_k

    def _call(self, request: ChoiceRequest) -> ChoiceDistribution:
        with self._lock:
            if self._stale is not None and not self._stale.done():
                raise BackendUnavailableError("上一次已 timeout 的推論尚未結束")
            self._stale = None
            future = self._executor.submit(self._backend.decide, request)
        try:
            return future.result(timeout=self._timeout_s)
        except (concurrent.futures.TimeoutError, TimeoutError):
            with self._lock:
                self._stale = future
            raise

    def _validate(self, distribution: ChoiceDistribution, expected: list[str]) -> dict[str, float]:
        raw = distribution.probabilities
        if not raw:
            raise _InvalidResponse(FallbackReason.EMPTY_RESPONSE, "模型回傳空分佈")
        unknown = sorted(set(raw) - set(expected))
        if unknown:
            raise _InvalidResponse(FallbackReason.UNKNOWN_CANDIDATE, f"不存在的候選 id：{unknown}")
        missing = [cid for cid in expected if cid not in raw]
        if missing:
            raise _InvalidResponse(FallbackReason.INVALID_PROBABILITY, f"分佈缺少候選：{missing}")
        cleaned = {cid: _validate_unit_interval(raw[cid], cid) for cid in expected}
        total = math.fsum(cleaned.values())  # type: ignore[arg-type]
        if abs(total - 1.0) > self._tolerance:
            raise _InvalidResponse(FallbackReason.INVALID_PROBABILITY, f"機率總和 {total:.6f} 不為 1")
        return cleaned  # type: ignore[return-value]

    def _fallback(
        self,
        candidates: Sequence[Candidate],
        started: float,
        reason: FallbackReason,
        detail: str,
        model_started: float,
        model_ms: float | None = None,
    ) -> RankingResult:
        return RankingResult(
            ranker=self._name,
            model=self.model_name,
            status=RankingStatus.FALLBACK,
            candidates=baseline_ranked(candidates),
            latency_ms=elapsed_ms(started),
            fallback=FallbackInfo(reason, detail),
            model_latency_ms=model_ms if model_ms is not None else elapsed_ms(model_started),
        )


def _validate_unit_interval(value: object, label: str) -> float | None:
    if value is None and label == "confidence":
        return None
    # bool 是 int 的子類別，True 會變成 1.0；這幾乎一定是協定錯誤。
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _InvalidResponse(FallbackReason.INVALID_PROBABILITY, f"{label} 型別不合法：{value!r}")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise _InvalidResponse(FallbackReason.INVALID_PROBABILITY, f"{label} 超出 [0, 1]：{value!r}")
    return number
