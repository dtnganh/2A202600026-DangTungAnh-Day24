# Failure Cluster Analysis

## Bottom 10 Questions

| # | Question | Type | F | AR | CP | CR | Avg | Cluster |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | What steps must be taken to control personal data violations and what are the conditions f | multi_context | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | C1 |
| 2 | What are the responsibilities of the government in ensuring compliance with data protectio | multi_context | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | C1 |
| 3 | What are the requirements for organizations in CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM regardin | multi_context | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | C1 |
| 4 | How do the rights of data subjects, particularly the right to delete data, relate to the t | reasoning | 0.00 | 0.00 | 0.00 | 0.25 | 0.06 | C3 |
| 5 | What does the phrase 'Độc lập - Tự do - Hạnh phúc' signify in the context of data privacy? | simple | 0.00 | 0.00 | 0.33 | 0.33 | 0.17 | C3 |
| 6 | What are the responsibilities of the government in data protection according to the regula | simple | 0.00 | 0.00 | 1.00 | 0.00 | 0.25 | C3 |
| 7 | Chủ thể dữ liệu là ai trong quy định về bảo vệ dữ liệu cá nhân? | simple | 0.50 | 0.82 | 0.00 | 0.00 | 0.33 | C2 |
| 8 | What is the significance of the mã số thuế in relation to the quyền riêng tư as outlined i | reasoning | 0.00 | 0.00 | 1.00 | 0.33 | 0.33 | C3 |
| 9 | What is the significance of the consent of the data subject in relation to the value-added | reasoning | 0.00 | 0.00 | 1.00 | 0.33 | 0.33 | C3 |
| 10 | What is the significance of the organization CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM in the con | simple | 0.00 | 0.00 | 1.00 | 0.50 | 0.37 | C3 |

## Clusters Identified

### Cluster C1: Multi-context retrieval gaps

**Pattern:** Multi-context retrieval gaps

**Examples:**
- What steps must be taken to control personal data violations and what are the conditions for transferring personal data abroad according to the regulations?
- What are the responsibilities of the government in ensuring compliance with data protection regulations as outlined in the recent decree on personal data protection?
- What are the requirements for organizations in CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM regarding personal data protection violations?

**Proposed fix:** Increase top_k, add hybrid retrieval or reranking, and inspect cross-document chunk coverage.

### Cluster C2: Noisy/off-topic retrieved contexts

**Pattern:** Noisy/off-topic retrieved contexts

**Examples:**
- Chủ thể dữ liệu là ai trong quy định về bảo vệ dữ liệu cá nhân?

**Proposed fix:** Tune retrieval filters, add metadata constraints, and rerank before generation.

### Cluster C3: Answer not fully grounded in context

**Pattern:** Answer not fully grounded in context

**Examples:**
- How do the rights of data subjects, particularly the right to delete data, relate to the tax deduction process outlined in the context of value-added tax?
- What does the phrase 'Độc lập - Tự do - Hạnh phúc' signify in the context of data privacy?
- What are the responsibilities of the government in data protection according to the regulations?

**Proposed fix:** Tighten grounded-generation prompt and cite only retrieved context spans.
