from typing import Literal
from langchain_core.tools import tool
from pydantic import BaseModel, Field

Operation = Literal[
    "sum",
    "average",
    "rank_desc",
    "rank_asc",
    "percentage",
    "growth_rate",
]

class StructuredCalculatorInput(BaseModel):
    operation: Operation = Field(
        ...,
        description="计算类型：sum、average、rank_desc、rank_asc、percentage、growth_rate",
    )

    values: list[float] = Field(
        ...,
        description="参与计算的数值列表",
        min_length=1,
    )

    labels: list[str] | None = Field(
        default=None,
        description="每个数值对应的标签，用于排名或结果展示",
    )
    base_value: float | None = Field(
        default=None,
        description="percentage 或 growth_rate 的基准值",
    )

def _validate_labels(values: list[float], labels: list[str] | None) -> list[str]:
    if labels is None:
        return [f"item_{idx + 1}" for idx in range(len(values))]
    if len(labels) != len(values):
        raise ValueError("labels 长度必须和 values 长度一致")
    return labels

@tool("structured_calculator", args_schema=StructuredCalculatorInput)
async def structured_calculator(
    operation: Operation,
    values: list[float],
    labels: list[str] | None = None,
    base_value: float | None = None,
) -> str:
    """执行受限结构化计算，支持求和、平均值、排名、百分比和增长率。"""

    if not values:
        return "计算失败：values 不能为空。"

    if operation == "sum":
        total = sum(values)
        return f"求和结果: {total}"

    if operation == "average":
        avg = sum(values) / len(values)
        return f"平均值: {avg}"
    
    if operation in {"rank_desc", "rank_asc"}:
        resolved_labels = _validate_labels(values, labels)
        pairs = list(zip(resolved_labels, values, strict=True))
        reverse = operation == "rank_desc"
        ranked = sorted(pairs, key=lambda x: x[1], reverse=reverse)

        lines = ["排名结果："]

        for idx, (label, value) in enumerate(ranked, start=1):
            lines.append(f"{idx}. {label}: {value}")
        
        return "\n".join(lines)
        
    return (
        "structured_calculator 已收到计算请求："
        f"operation={operation}, values={values}, labels={labels}, base_value={base_value}"
    )




