# 参考文献双源校验（Crossref + Europe PMC）

判定口径：MATCH = 至少一源命中且题名相似度 ≥ 0.90 或 DOI/PMID 直接一致；
NOT_FOUND = 两源均正常应答但无匹配（真"查不到"）；
SERVICE_ERROR = 服务不可用/超时/解析失败（**不得计为查不到**）。

| # | 判定 | Crossref | Europe PMC | 题名/DOI |
|---|---|---|---|---|
| 1 | MATCH | NO_HIT(最佳 0.72) | OK(题名 1.00) | Dementia prevention, intervention, and care: 2024 report of the |
| 2 | MATCH | NO_HIT(最佳 0.40) | OK(题名 1.00) | Estimation of the global prevalence of dementia in 2019 and forecasted |
| 3 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Geriatric syndromes: clinical, research, and policy implications of a  |
| 4 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Frailty in relation to the accumulation of deficits |
| 5 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Frailty trajectories preceding dementia in the US and UK |
| 6 | MATCH | OK(DOI) | OK(ID) | Changes in frailty and its association with dementia risk in four pros |
| 7 | MATCH | OK(DOI) | OK(ID) | Longitudinal dynamics in frailty and incident all-cause dementia: a mu |
| 8 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Association between multimorbidity and the risk of dementia: a systema |
| 9 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Multimorbidity and risk of dementia: a systematic review and meta-anal |
| 10 | MATCH | OK(题名 1.00) | NO_HIT | Late-life depression and risk of vascular dementia and Alzheimer's dis |
| 11 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Depression and risk for Alzheimer disease: systematic review, meta-ana |
| 12 | MATCH | OK(题名 1.00) | NO_HIT | Baseline disability in activities of daily living predicts dementia ri |
| 13 | MATCH | OK(题名 1.00) | NO_HIT | Disability in basic and instrumental activities of daily living is ass |
| 14 | MATCH | OK(题名 1.00) | NO_HIT | Effects of physical and psychological multimorbidity on the risk of de |
| 15 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Associations of physical frailty, depression and their interaction wit |
| 16 | MATCH | OK(题名 1.00) | OK(题名 1.00) | The lifetime accumulation of multimorbidity and its influence on demen |
| 17 | MATCH | NO_HIT(最佳 0.45) | OK(题名 1.00) | Geriatric syndromes and mortality among hospitalized older adults |
| 18 | N/A(数据源/网址条目) | SKIP | SKIP | Gateway to Global Aging Data. Center for Economic and Social Research, |
| 19 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Cohort profile: the China Health and Retirement Longitudinal Study (CH |
| 20 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Cohort profile: the English Longitudinal Study of Ageing |
| 21 | MATCH | NO_HIT(最佳 0.07) | OK(题名 1.00) | Cohort profile: the Health and Retirement Study (HRS) |
| 22 | N/A(数据源/网址条目) | SKIP | SKIP | Korean Longitudinal Study of Ageing (KLoSA). Korea Employment Informat |
| 23 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Cohort profile: the Mexican Health and Aging Study (MHAS) |
| 24 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Data resource profile: the Survey of Health, Ageing and Retirement in  |
| 25 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Studies of illness in the aged: the index of ADL, a standardized measu |
| 26 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Assessment of older people: self-maintaining and instrumental activiti |
| 27 | MATCH | OK(题名 1.00) | OK(题名 1.00) | A new method of classifying prognostic comorbidity in longitudinal stu |
| 28 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Screening for depression in well older adults: evaluation of a short f |
| 29 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Development of the EURO-D scale: a European Union initiative to compar |
| 30 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Assessment of cognition using surveys and neuropsychological assessmen |
| 31 | MATCH | OK(题名 1.00) | OK(题名 1.00) | A comparison of the prevalence of dementia in the United States in 200 |
| 32 | MATCH | OK(题名 1.00) | NO_HIT(最佳 0.12) | Meta-analysis in clinical trials |
| 33 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Measuring inconsistency in meta-analyses |
| 34 | MATCH | OK(题名 1.00) | NO_HIT(最佳 0.72) | A unification of mediation and interaction: a four-way decomposition |
| 35 | MATCH | NO_HIT(最佳 0.12) | OK(题名 1.00) | Mediation analysis: a practitioner's guide |
| 36 | MATCH | OK(题名 1.00) | NO_HIT | A proportional hazards model for the subdistribution of a competing ri |
| 37 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Sensitivity analysis in observational research: introducing the E-valu |
| 38 | MATCH | OK(题名 1.00) | OK(题名 1.00) | Imputing missing covariate values for the Cox model |

**第一轮汇总**：共 38 条；MATCH 36；NOT_FOUND 0；N/A 2；SERVICE_ERROR 0