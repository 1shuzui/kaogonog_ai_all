"""Re-evaluate only confirmed empty-evidence failures; dry-run by default.

Run with the backend venv and PYTHONPATH pointing at the deployed backend.
Private backups contain original answers and must remain outside Git/web roots.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from app.db.session import SessionLocal
from app.models.entities import ExamAnswer, HistoryRecord
from app.services.scoring_service import _persist_result, evaluate_answer


def is_empty_evidence_failure(answer):
    result = answer.score_result if isinstance(answer.score_result, dict) else {}
    trace = result.get("scoringTrace") or {}
    comment = str(result.get("aiComment") or "")
    return (
        bool(str(answer.transcript or "").strip())
        and result.get("scoringMode") == "llm"
        and result.get("totalScore") == 0
        and bool(trace.get("stageTwoPrompt"))
        and not trace.get("directResult")
        and any(marker in comment for marker in ("证据包为空", "证据包无任何证据", "证据包无内容"))
    )


async def run(args):
    with SessionLocal() as db:
        answers = [a for a in db.query(ExamAnswer).all() if is_empty_evidence_failure(a)]
        print(json.dumps({"candidates": len(answers), "apply": args.apply}), flush=True)
        for answer in answers:
            print(json.dumps({"examId": answer.exam_id, "questionId": answer.question_id,
                              "transcriptChars": len(answer.transcript)}, ensure_ascii=False), flush=True)
        if not args.apply or not answers:
            return
        backup_dir = Path(args.backup_dir).resolve()
        backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup_path = backup_dir / ("empty-evidence-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        histories = db.query(HistoryRecord).filter(HistoryRecord.exam_id.in_({a.exam_id for a in answers})).all()
        snapshot = {
            "answers": [{"examId": a.exam_id, "questionId": a.question_id, "transcript": a.transcript,
                         "answeredAt": str(a.answered_at), "scoreResult": a.score_result} for a in answers],
            "histories": [{column.name: getattr(h, column.name) for column in h.__table__.columns} for h in histories],
        }
        fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, default=str)
        print(json.dumps({"backup": str(backup_path)}), flush=True)
        for answer in answers:
            old_text, old_result, old_time = answer.transcript, answer.score_result, answer.answered_at
            # Compute first, with no exam_id: failed/fallback scoring cannot overwrite the record.
            result = await evaluate_answer(db, answer.question_id, old_text, None)
            if result.get("scoringMode") != "llm":
                raise RuntimeError("External model did not complete; original record left intact")
            db.refresh(answer)
            if answer.transcript != old_text or answer.score_result != old_result:
                raise RuntimeError("Answer changed during repair; refusing to overwrite it")
            for key in ("answerTiming", "skipReason", "asrFailureType", "asrMessage"):
                if key in old_result:
                    result[key] = old_result[key]
            _persist_result(db, answer.exam_id, answer.question_id, old_text, result)
            answer.answered_at = old_time
            db.commit()
            print(json.dumps({"repaired": True, "examId": answer.exam_id,
                              "questionId": answer.question_id, "score": result["totalScore"],
                              "mode": result["scoringMode"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir")
    args = parser.parse_args()
    if args.apply and not args.backup_dir:
        parser.error("--apply requires --backup-dir outside Git and web roots")
    asyncio.run(run(args))
