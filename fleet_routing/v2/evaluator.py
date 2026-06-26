"""Expression tree evaluator for rule engine v2."""

from __future__ import annotations

from core_data.models import TripRequest, Vehicle
from fleet_routing.v2.context import EvalContext
from fleet_routing.v2.metrics import REGISTRY, MetricValue
from fleet_routing.v2.models import CompareOpV2, ExprNode, ExprOp, MetricRef


def _numeric(value: MetricValue) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str):
        return 0.0
    return float(value)


def _compare(left: float, op: CompareOpV2, right: float, right_max: float | None = None) -> bool:
    if op == CompareOpV2.EQ:
        return abs(left - right) < 1e-9
    if op == CompareOpV2.NE:
        return abs(left - right) >= 1e-9
    if op == CompareOpV2.LT:
        return left < right
    if op == CompareOpV2.LTE:
        return left <= right
    if op == CompareOpV2.GT:
        return left > right
    if op == CompareOpV2.GTE:
        return left >= right
    if op == CompareOpV2.BETWEEN and right_max is not None:
        return right <= left <= right_max
    return False


def resolve_metric(
    ctx: EvalContext,
    ref: MetricRef,
    *,
    vehicle: Vehicle | None = None,
    trip: TripRequest | None = None,
    constants: dict[str, float] | None = None,
) -> MetricValue:
    """Compute a metric reference."""
    zone = str(ref.params.get("zone", "")) or None
    if ref.id == "const.value":
        name = str(ref.params.get("name", ""))
        return ctx.const(constants or {}, name, 0.0)
    return REGISTRY.compute(
        ref.id,
        ctx,
        vehicle=vehicle,
        trip=trip,
        zone=zone,
        constants=constants,
        params=dict(ref.params),
    )


def evaluate_expr(
    node: ExprNode,
    ctx: EvalContext,
    *,
    vehicle: Vehicle | None = None,
    trip: TripRequest | None = None,
    constants: dict[str, float] | None = None,
) -> bool:
    """Return True if expression matches."""
    if node.op == ExprOp.AND:
        return all(evaluate_expr(c, ctx, vehicle=vehicle, trip=trip, constants=constants) for c in node.children)
    if node.op == ExprOp.OR:
        return any(evaluate_expr(c, ctx, vehicle=vehicle, trip=trip, constants=constants) for c in node.children)
    if node.op == ExprOp.NOT:
        if not node.children:
            return True
        return not evaluate_expr(node.children[0], ctx, vehicle=vehicle, trip=trip, constants=constants)
    if node.op == ExprOp.CONST:
        return bool(node.value)
    if node.op == ExprOp.METRIC and node.metric is not None:
        val = resolve_metric(ctx, node.metric, vehicle=vehicle, trip=trip, constants=constants)
        if isinstance(val, bool):
            return val
        return _numeric(val) != 0.0
    if node.op == ExprOp.COMPARE and node.metric is not None and node.operator is not None:
        left = _numeric(resolve_metric(ctx, node.metric, vehicle=vehicle, trip=trip, constants=constants))
        if node.right_metric is not None:
            right = _numeric(resolve_metric(ctx, node.right_metric, vehicle=vehicle, trip=trip, constants=constants))
        else:
            right = node.value or 0.0
        return _compare(left, node.operator, right, node.value_max)
    return False


def collect_metric_snapshot(
    node: ExprNode,
    ctx: EvalContext,
    *,
    vehicle: Vehicle | None = None,
    trip: TripRequest | None = None,
    constants: dict[str, float] | None = None,
) -> dict[str, float | int | bool | str]:
    """Collect metric values referenced in an expression for audit."""
    out: dict[str, float | int | bool | str] = {}

    def walk(n: ExprNode) -> None:
        if n.metric is not None:
            out[n.metric.id] = resolve_metric(ctx, n.metric, vehicle=vehicle, trip=trip, constants=constants)
        if n.right_metric is not None:
            out[n.right_metric.id] = resolve_metric(ctx, n.right_metric, vehicle=vehicle, trip=trip, constants=constants)
        for c in n.children:
            walk(c)

    walk(node)
    return out
