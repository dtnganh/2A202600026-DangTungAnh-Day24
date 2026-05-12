# Prompts AI đã dùng trong Lab 24

File này ghi lại các prompt/chỉ dẫn AI đã sử dụng trong quá trình làm Lab 24 để đảm bảo academic integrity. Các kết quả cuối cùng đã được kiểm tra lại bằng script và bằng review thủ công, không copy mù từ AI.

## 1. Repo planning and checklist

**Prompt tóm tắt:** Đọc `lab24-student-edition.md`, giải thích nội dung lab và tạo `todo.md` liệt kê toàn bộ việc cần làm để đạt full điểm.

**Mục đích sử dụng:** Hiểu rubric, chia Phase A/B/C/D thành checklist triển khai, xác định artifact bắt buộc.

**Cách kiểm chứng:** Đối chiếu lại với self-assessment checklist trong đề lab.

## 2. Phase A - RAGAS evaluation

**Prompt tóm tắt:** Viết script tạo synthetic test set, chạy RAGAS 4 metrics, sinh `ragas_results.csv`, `ragas_summary.json`, và phân tích failure clusters.

**Mục đích sử dụng:** Sinh code scaffold cho `phase-a/generate_testset.py`, `phase-a/run_eval.py`, `phase-a/failure_analysis.py`.

**Cách kiểm chứng:** Chạy script bằng venv của lab, kiểm tra `testset_v1.csv` có 51 rows, đủ cột `question`, `ground_truth`, `contexts`, `evolution_type`; kiểm tra `ragas_results.csv` có 4 metric columns.

## 3. Phase B - LLM-as-Judge

**Prompt tóm tắt:** Xây pairwise judge có swap-and-average, absolute scoring rubric 4 chiều, Cohen's kappa calibration và bias report.

**Mục đích sử dụng:** Tạo `phase-b/judge.py`, `kappa_analysis.py`, `bias_report.py`, sau đó chạy với OpenAI `gpt-4o-mini`.

**Cách kiểm chứng:** Kiểm tra `pairwise_results.csv` có 30 rows, `absolute_scores.csv` có 30 rows, `human_labels.csv` có 10 labels, `kappa_summary.json` có Cohen's kappa.

## 4. Phase C - Guardrails

**Prompt tóm tắt:** Implement input guardrail cho PII redaction, topic guard, adversarial testing, output guard qua Groq, full pipeline benchmark và audit log.

**Mục đích sử dụng:** Tạo `phase-c/input_guard.py`, `output_guard.py`, `run_guardrail_tests.py`, `full_pipeline.py`.

**Cách kiểm chứng:** Chạy test guardrails và benchmark. Kết quả hiện tại: PII recall 85.7%, topic accuracy 80.0%, adversarial detection 100.0%, output safety detection 100.0%, full pipeline benchmark 100 requests.

## 5. Phase D - Blueprint and submission docs

**Prompt tóm tắt:** Viết `blueprint.md` gồm SLOs, architecture diagram, alert playbook và cost analysis; cập nhật README theo artifact thật.

**Mục đích sử dụng:** Tạo tài liệu nộp bài dễ đọc, bám đúng rubric và nêu rõ deviation khi Groq decommission Llama Guard 3/4.

**Cách kiểm chứng:** Đọc lại `README.md`, `phase-d/blueprint.md`, chạy `check_lab.py`, kiểm tra Git không track `.env`, `venv/`, `todo.md`.

## 6. Lưu ý về sử dụng AI

- AI hỗ trợ sinh code và tài liệu ban đầu.
- Người làm bài đã yêu cầu không bịa số liệu; các số trong README lấy từ artifact thật.
- Những phần không đạt target, ví dụ L3 latency của Groq safety fallback, được ghi rõ thay vì che giấu.
