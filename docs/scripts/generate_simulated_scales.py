from __future__ import annotations

import argparse
import json
from pathlib import Path

SCL90_DIM_TEXTS = {
    "somatization": [
        "最近一周我常有不明原因的头痛或身体酸痛。",
        "最近一周我会反复感到胃部不适或食欲异常。",
        "最近一周我容易出现心慌、胸闷等身体反应。",
        "最近一周我经常感觉精力不足、身体沉重。",
        "最近一周我会担心自己身体出现严重问题。",
        "最近一周我会因为身体小毛病而明显紧张。",
        "最近一周我常感到四肢乏力或发软。",
        "最近一周我会被睡眠相关的身体不适困扰。",
        "最近一周我的身体状态影响了学习/生活节奏。",
    ],
    "compulsive": [
        "最近一周我会反复检查同一件事是否完成。",
        "最近一周我很难停止脑中重复出现的念头。",
        "最近一周我做事会过度追求完美而拖延。",
        "最近一周我常因担心出错而重复确认细节。",
        "最近一周我会反复回想已发生的小失误。",
        "最近一周我在学习时常被“必须这样做”困住。",
        "最近一周我会因反复犹豫而难以下决定。",
        "最近一周我会按固定顺序做事，否则不安。",
        "最近一周我会因反复整理/重做而耗费很多时间。",
    ],
    "interpersonal": [
        "最近一周我在人际互动中容易紧张或不自在。",
        "最近一周我会过度在意别人对我的看法。",
        "最近一周我与同学沟通时担心被否定。",
        "最近一周我会因为社交场合而感到明显压力。",
        "最近一周我在人多场景里容易感到拘谨。",
        "最近一周我会避免主动表达自己的真实想法。",
        "最近一周我在人际冲突后会持续自责。",
        "最近一周我感觉自己不太容易被他人理解。",
        "最近一周我与他人相处时常感到被比较或被评判。",
    ],
    "depression": [
        "最近一周我对原本感兴趣的事情提不起劲。",
        "最近一周我经常感到情绪低落或无助。",
        "最近一周我会觉得做什么都没有意义。",
        "最近一周我比平时更容易疲惫、动力不足。",
        "最近一周我会对自己产生明显否定感。",
        "最近一周我常觉得未来看起来缺乏希望。",
        "最近一周我难以从日常小事中感到愉快。",
        "最近一周我会持续处在压抑的心情中。",
        "最近一周我会因为情绪问题影响学习效率。",
    ],
    "anxiety": [
        "最近一周我经常感到紧张、担忧难以放松。",
        "最近一周我会因为小事反复焦虑。",
        "最近一周我容易出现坐立不安的状态。",
        "最近一周我会对未发生的事情提前担心。",
        "最近一周我在压力情境下容易慌乱。",
        "最近一周我难以让自己平静下来。",
        "最近一周我会因学习任务产生持续焦虑感。",
        "最近一周我在夜间更容易出现担心和烦躁。",
        "最近一周焦虑情绪已影响我的专注与休息。",
    ],
    "hostility": [
        "最近一周我比平时更容易烦躁或发脾气。",
        "最近一周我会对他人的言行产生明显不满。",
        "最近一周我常有“容易被激怒”的体验。",
        "最近一周我在人际摩擦中更难控制情绪。",
        "最近一周我会因小冲突持续生气。",
        "最近一周我对周围环境更容易产生敌意。",
        "最近一周我会在沟通中不自觉提高语气。",
        "最近一周我会因压力大而迁怒他人。",
        "最近一周我经常感觉心里憋闷、想发泄。",
    ],
    "phobic": [
        "最近一周我在特定场景会出现明显害怕感。",
        "最近一周我会因为陌生环境而回避出行。",
        "最近一周我在公开场合容易紧张到想逃离。",
        "最近一周我会担心某些情境发生失控。",
        "最近一周我会因恐惧而主动减少社交活动。",
        "最近一周我在人群密集处会明显不安。",
        "最近一周我会回避自己觉得“危险”的地点。",
        "最近一周我在考试/汇报前会出现强烈害怕。",
        "最近一周恐惧情绪已影响我正常安排。",
    ],
    "paranoid": [
        "最近一周我会怀疑他人对我有负面意图。",
        "最近一周我容易把中性言行理解成针对我。",
        "最近一周我会担心别人背后议论自己。",
        "最近一周我在人际中更容易保持防备状态。",
        "最近一周我会对他人评价过度敏感。",
        "最近一周我常担心自己被误解或被针对。",
        "最近一周我对周围人的信任感有所下降。",
        "最近一周我会反复揣测他人的真实想法。",
        "最近一周我在团队协作中更难放松。",
    ],
    "psychoticism": [
        "最近一周我会感到与周围人有明显疏离感。",
        "最近一周我偶尔会有不真实或恍惚的感觉。",
        "最近一周我会觉得自己的想法难被理解。",
        "最近一周我感到思路有时变得混乱。",
        "最近一周我会出现难以描述的怪异不适感。",
        "最近一周我会因心理压力感到“脱节”。",
        "最近一周我在情绪波动时会有失控担忧。",
        "最近一周我会觉得自己和环境不太协调。",
        "最近一周我经常感到内心紧绷又难以言说。",
    ],
    "additional": [
        "最近一周我的睡眠质量明显下降。",
        "最近一周我在起床后仍感到疲惫。",
        "最近一周我的食欲较平时变化明显。",
        "最近一周我会因情绪问题影响日常效率。",
        "最近一周我更容易因小问题反复担忧。",
        "最近一周我会对未来安排感到迷茫。",
        "最近一周我难以维持稳定的学习节奏。",
        "最近一周我会觉得身心都处在高压状态。",
        "最近一周我需要更多支持才能维持状态。",
    ],
}

SAS_TEXTS = [
    "我会无明显原因地感到紧张不安。",
    "我容易因为小事而心里发慌。",
    "我在安静时也会感到难以放松。",
    "我常担心不好的事情会发生在自己身上。",
    "我在学习任务前会过度紧张。",
    "我会出现坐立不安、难以静下来的情况。",
    "我常觉得心跳加快或有紧迫感。",
    "我会因未来不确定而持续担忧。",
    "我容易因为他人评价而焦虑。",
    "我在睡前常因担心而难以入睡。",
    "我经常感觉神经绷得很紧。",
    "我在压力下会明显烦躁。",
    "我会反复思考同一件担心的事。",
    "我在公共场合容易紧张。",
    "我会因学习节奏而感到持续焦虑。",
    "我常担心自己表现不够好。",
    "我在突发变化面前容易慌乱。",
    "我近期更容易疲惫且难以恢复。",
    "我会因焦虑影响专注力。",
    "我总体上感觉焦虑程度较高。",
]

SDS_TEXTS = [
    "我最近情绪低落的时间变多了。",
    "我对曾经喜欢的事情兴趣下降。",
    "我会觉得做事提不起精神。",
    "我常感到疲惫、动力不足。",
    "我会觉得自己价值感降低。",
    "我对未来有时缺乏希望。",
    "我在学习中容易感到无力。",
    "我比平时更想独处。",
    "我在社交中变得被动。",
    "我会出现持续性的消极想法。",
    "我最近做事效率明显下降。",
    "我会因情绪问题影响作息。",
    "我常觉得开心变得困难。",
    "我会否定自己的能力与表现。",
    "我有时觉得生活缺少意义感。",
    "我面对压力时更容易沮丧。",
    "我最近容易陷入自责情绪。",
    "我会因小挫折而情绪下滑很久。",
    "我总体上感到情绪较压抑。",
    "我感觉需要外部支持来调整状态。",
]


def _build_scl90_questions() -> list[dict]:
    dims = [
        "somatization",
        "compulsive",
        "interpersonal",
        "depression",
        "anxiety",
        "hostility",
        "phobic",
        "paranoid",
        "psychoticism",
        "additional",
    ]
    questions = []
    for idx in range(1, 91):
        dim = dims[(idx - 1) // 9]
        text = SCL90_DIM_TEXTS[dim][(idx - 1) % 9]
        questions.append(
            {
                "id": idx,
                "text": f"SCL90模拟题{idx:02d}：{text}",
                "dimension": dim,
                "weight": 1,
                "min": 1,
                "max": 5,
            }
        )
    return questions


def _build_sas_questions() -> list[dict]:
    reverse_ids = {5, 9, 13, 17, 19}
    questions = []
    for idx in range(1, 21):
        q = {
            "id": idx,
            "text": f"SAS模拟题{idx:02d}：{SAS_TEXTS[idx - 1]}",
            "dimension": "anxiety",
            "weight": 1,
            "min": 1,
            "max": 4,
        }
        if idx in reverse_ids:
            q["reverse"] = True
        questions.append(q)
    return questions


def _build_sds_questions() -> list[dict]:
    reverse_ids = {2, 5, 6, 11, 12, 14, 16, 17, 18, 20}
    questions = []
    for idx in range(1, 21):
        q = {
            "id": idx,
            "text": f"SDS模拟题{idx:02d}：{SDS_TEXTS[idx - 1]}",
            "dimension": "depression",
            "weight": 1,
            "min": 1,
            "max": 4,
        }
        if idx in reverse_ids:
            q["reverse"] = True
        questions.append(q)
    return questions


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate simulated SCL-90/SAS/SDS templates")
    parser.add_argument(
        "--out-dir",
        default="docs/scales",
        help="Directory for generated json files (default: docs/scales)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()

    scl90 = {
        "name": "SCL-90 结构化模拟量表（90题）",
        "scale_type": "scl90_sample",
        "description": "结构化模拟题库（非版权原题），用于流程联调与模型接口验证。",
        "questions": _build_scl90_questions(),
    }
    sas = {
        "name": "SAS 结构化模拟量表（20题）",
        "scale_type": "sas_sample",
        "description": "结构化模拟题库（非版权原题），包含反向计分标记。",
        "questions": _build_sas_questions(),
    }
    sds = {
        "name": "SDS 结构化模拟量表（20题）",
        "scale_type": "sds_sample",
        "description": "结构化模拟题库（非版权原题），包含反向计分标记。",
        "questions": _build_sds_questions(),
    }

    _write_json(out_dir / "scl90_simulated_full.json", scl90)
    _write_json(out_dir / "sas_simulated_full.json", sas)
    _write_json(out_dir / "sds_simulated_full.json", sds)
    print(f"Generated templates into: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
