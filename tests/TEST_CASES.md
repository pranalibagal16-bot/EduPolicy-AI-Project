# Manual test cases (Day 13)

Use `sample_docs/college_policy.docx` (or your own documents).

| # | Scenario | Input | Expected |
|---|----------|-------|----------|
| 1 | Correct question | "What is the attendance requirement for first-year students?" | Answer mentioning 75%, with document name + section/page |
| 2 | Unrelated question | "Who won the football world cup?" | "I could not find this information in the uploaded documents." and no sources |
| 3 | Not in documents | "What is the hostel fee?" (not in file) | Same not-found message |
| 4 | Multiple documents | Upload 2+ files, ask something from the 2nd | Citation names the 2nd file |
| 5 | Filter by document | Select one file in sidebar, ask about another file | Not-found message |
| 6 | Large document | Upload 100+ page PDF | Upload succeeds; questions answered; note processing time |
| 7 | Delete document | Delete a file, repeat its question | Not-found message |
| 8 | Wrong file type | Upload .txt | Rejected (frontend filters, API returns 400) |
| 9 | Scanned PDF | Upload image-only PDF | 422 "No extractable text found" |
| 10 | Role check | Log in as `student` | No upload/delete controls; API returns 403 |
| 11 | Chat history | Ask 2 questions, refresh page | Both Q&As still shown |

Automated: `pytest -q`
