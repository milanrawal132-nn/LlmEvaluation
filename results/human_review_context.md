# Human review context — Phase 6 pilot

Label in `results/human_review_template.csv`. Use `1` for yes, `0` for no.

- **human_correct** — does the model answer state the same facts as the reference? Different units for the same amount still count as correct. If the reference states several facts, all of them are required.
- **human_faithful** — is every claim in the model answer supported by the retrieved context below? Judge *support*, not truth: a claim that is true in the real world but absent from the context is NOT faithful.
- **human_relevant** — does the answer address the question asked? Ignore whether it is correct. Right topic with wrong numbers is still relevant.
- **notes** — anything ambiguous. These are the rows worth arguing about.

An `I don't know.` answer counts as faithful and relevant (it asserts nothing and does address the question), and never correct.

The judge's verdicts are deliberately not shown. Label independently, then run `scripts/compare_judge_to_human.py`.

## q001

**Question:** Did Ecoplast declare a dividend for the year 2025-26?

**Reference answer:** No. The Board decided not to recommend a dividend for the financial year 2025-26.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.47, 48 — score 0.655</summary>

```
on the website of the Company at 
www.ecoplastindia.com. 
 
ANNUAL RETURN: 
Pursuant to Section 92(3) and 134(3)(a) of the Act and the Companies (Management and 
Administration) Rules, 2014, the Annual Return for FY 25-26 is available on the website 
of the Company at www.ecoplastindia.com. 
 
 
43
  
AUDITORS:  
As per the provisions of Section 139 of the Act read with the Companies (Audit and 
Auditors) Rules, 2014, M/s. Y.B. Desai & Associates, Chartered Accountants, Surat, 
(ICAI Registratio
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.1, 2, 3 — score 0.650</summary>

```
.ecoplastindia.com 
 
We request you to take the same on record. 
 
Thanking you 
 
Yours faithfully 
For Ecoplast Limited 
 
 
 
Rakesh Kumar Kumawat 
Company Secretary & Compliance Officer 
 
Encl: As above 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
  Ecoplast Limited 
 
 
 
44th Annual Report 2025-26 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
44 
Ecoplast Limited 
 
 Annual Report 2025-26  
   
Board of Directors 
(as on 31.03.2026)
 
B R Tarafdar -  Chairman & Independent Directo
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.10 — score 0.646</summary>

```
 year 2025-26 will be also available on the Company’s 
Website: www.ecoplastindia.com for download. 
 
10. All documents referred to in the notice of the Meeting and the explanatory 
statement and other statutory registers shall be available for inspection by the 
Members at the registered office of the Company during office hours on all working 
days between 11.00 A.M. and 1.00 P.M. except Saturdays, Sundays and public 
holidays, from the date hereof up to the date of the Annual General Meeting
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.218, 219 — score 0.643</summary>

```
0th May, 2026 Date : 30th May, 2026
The Financial Statements were authorised for issue in accordance with a resolution of the Board of Dire ctors in its meeting held on May 30, 2026.
Previous periods/ years figures have been reworked/regrouped/ reclassified, wherever necessary, to make them comparable with the figures of the current periods / years and after
considering the effect of the merger as stated herein above.
214
ECOPLAST LIMITED 
Regd.  Office: National Highway No. 8, Water Works Cross
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.138 — score 0.636</summary>

```
2,388 5.86%
As at 31st March, 2026                2,02,388 5.86%
Ecoplast Limited
Particulars
The Paid-up Capital includes 1,500,000 Equity Shares of Rs.10 each allotted as fully paid up Bonus shares by capitalisingRs. 50.00 lacs out of General Reserve and Rs. 100.00 lacs
out of Revaluation Reserve prior to listing of Company 's Equity Shares.
The holders of equity shares will be entitled to receive remaining assets of the Company, after distribution of all preferential amounts in the event of l
```

</details>

---

## q002

**Question:** How many board meetings did Ecoplast hold during 2025-26?

**Reference answer:** Nine.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.40 — score 0.677</summary>

```
s number of meetings of the Board attended during the year, 
remuneration drawn, please refer to the corporate governance report which is a part of 
this Annual Report. 
 
Registered Office: 
National Highway No. 8, 
Water Works Cross Road, Abrama,  
Valsad- 396001, Gujarat 
CIN: L25200GJ1981PLC004375 
Tel: 9879554138 
E-mail : investor@ecoplastindia.com,  
Website : www.ecoplastindia.com 
 
Date: May 30, 2026 
Place: Valsad 
By Order of the Board 
For Ecoplast Limited 
 
   
Rakesh Kumar Kumawa
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.1, 2, 3 — score 0.647</summary>

```
.ecoplastindia.com 
 
We request you to take the same on record. 
 
Thanking you 
 
Yours faithfully 
For Ecoplast Limited 
 
 
 
Rakesh Kumar Kumawat 
Company Secretary & Compliance Officer 
 
Encl: As above 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
  Ecoplast Limited 
 
 
 
44th Annual Report 2025-26 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
44 
Ecoplast Limited 
 
 Annual Report 2025-26  
   
Board of Directors 
(as on 31.03.2026)
 
B R Tarafdar -  Chairman & Independent Directo
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.10 — score 0.637</summary>

```
 year 2025-26 will be also available on the Company’s 
Website: www.ecoplastindia.com for download. 
 
10. All documents referred to in the notice of the Meeting and the explanatory 
statement and other statutory registers shall be available for inspection by the 
Members at the registered office of the Company during office hours on all working 
days between 11.00 A.M. and 1.00 P.M. except Saturdays, Sundays and public 
holidays, from the date hereof up to the date of the Annual General Meeting
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.4, 5 — score 0.620</summary>

```
...............170 
 
Notes to the Consolidated Financial Statements….........172 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
NOTICE 
 
Notice is hereby given that the 44th Annual General Meeting of the members of Ecoplast 
Limited will be held on Monday, September 07, 2026 at 3.30 P.M. at ‘Shantivan Resort’, 
Atul-Valsad Road, Vashiyar, Valsad, Gujarat- 396001, India to transact the following 
business: 
 
ORDINARY BUSINESS: 
 
1. To receive, consider and adopt: 
a. the audited standalone financial statements
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.218, 219 — score 0.615</summary>

```
0th May, 2026 Date : 30th May, 2026
The Financial Statements were authorised for issue in accordance with a resolution of the Board of Dire ctors in its meeting held on May 30, 2026.
Previous periods/ years figures have been reworked/regrouped/ reclassified, wherever necessary, to make them comparable with the figures of the current periods / years and after
considering the effect of the merger as stated herein above.
214
ECOPLAST LIMITED 
Regd.  Office: National Highway No. 8, Water Works Cross
```

</details>

---

## q003

**Question:** On what date was Priyal Saurabh Vora made an independent director at Ecoplast?

**Reference answer:** 27 May 2025, for a five-year term running 1 June 2025 to 31 May 2030.

**Model answer:** Priyal Saurabh Vora was made an independent director at Ecoplast on August 12, 2025.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.98, 99 — score 0.652</summary>

```
                                                                                                    For Ecoplast Limited 
  
 
 
                                                           Jaymin B. Desai 
                                    Managing Director 
 Date: May 30, 2026                                                                                      DIN: 00156221                   
 Place: Valsad        
  
94
 
 
 
CHIEF EXECUTIVE OFFICER (CEO) & CHIEF FINANCIAL OFFICER (CFO) 
CERT
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.19, 20 — score 0.651</summary>

```
Website : www.ecoplastindia.com 
 
Date: May 30, 2026 
Place: Valsad 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
By Order of the Board 
For Ecoplast Limited 
 
   
Rakesh Kumar Kumawat 
Company Secretary &  
Compliance Officer 
ICSI M. No. A37556 
 
15
EXPLANATORY STATEMENT PURSUANT TO SECTION 102 OF THE COMPANIES 
ACT, 2013 
 
Item No. 3 
 
The Members of the Company had appointed Mr. Jaymin B. Desai as Managing Director 
of the Company for a period of 3 years with effect from October 
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.44 — score 0.643</summary>

```
m June 01, 2025 to May 31, 2030. The said appointment of Ms. 
Priyal Saurabh Vora as an Independent Director (ID) was approved by the Members at 
the AGM held on August 12, 2025.  
Based on recommendation of NRC, Board and in accordance with provisions of the Act 
and Listing Regulations, Mr. Jayesh Jashvantlal Shah (DIN: 00260876) was appointed as 
an Additional Director (Independent) of the Company by the Board of Directors on 
January 01, 2026, for a term commencing from January 01, 2026 up t
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.1, 2, 3 — score 0.619</summary>

```
.ecoplastindia.com 
 
We request you to take the same on record. 
 
Thanking you 
 
Yours faithfully 
For Ecoplast Limited 
 
 
 
Rakesh Kumar Kumawat 
Company Secretary & Compliance Officer 
 
Encl: As above 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
  Ecoplast Limited 
 
 
 
44th Annual Report 2025-26 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
44 
Ecoplast Limited 
 
 Annual Report 2025-26  
   
Board of Directors 
(as on 31.03.2026)
 
B R Tarafdar -  Chairman & Independent Directo
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.44 — score 0.612</summary>

```
RSONNEL: 
Based on the recommendation of the Nomination and Remuneration Committee (NRC) 
and the Board, and in accordance with the provisions of the Act and SEBI (Listing 
Obligations and Disclosure Requirements) Regulations, 2015 (“List ing Regulations”),  
Ms. Priyal Saurabh Vora (DIN: 09374896) was appointed as an Additional Director 
(Independent) of the Company by the Board of Directors on May 27, 2025, for a term of 5 
years commencing from June 01, 2025 to May 31, 2030. The said appointm
```

</details>

---

## q004

**Question:** Which business was folded into Ecoplast and from when?

**Reference answer:** Kunal Plastics Private Limited, under an NCLT-sanctioned merger with an appointed date of 1 April 2025.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.66 — score 0.649</summary>

```
a. Ecoplast Ltd. specializes in producing 
high-quality, multilayer coextruded polyethylene and co-polymer films with an 
annual capacity of 9600 MT.  
Since its inception in 1981, the Company had played a major role in the development 
of the flexible packaging industry in India by supplying lamination grade films. 
However, in view of poor margins and fierce competition in the commodity 
lamination business, the company transitioned into only Value-added product 
business. Since 2024 the focus
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.43 — score 0.594</summary>

```
s serving the hygiene sector in India. We also have exports 
into the United States and African markets catering to the hospitality and food industry 
respectively. With this merger, all the business and operating entities within the group 
now stand consolidated under Ecoplast Limited.  
 
Increased trade tariffs announced by the USA on India, and the resulting uncertainty, 
affected export orders and realizations during the year. The Company is responding by 
concentrating its efforts on devel
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.121 — score 0.570</summary>

```
ar ended 31st March, 2026
Corporate Information
Ecoplast Limited is Public Company domiciled in India and incorporated under the provisions of the Companies Act, 1956 having Corporate Identity
Number L25200GJ1981PLC004375. Its shares are listed on BombayStock Exchange in India. The Company is engaged in the business of manufacturing,
processing and selling of Co-extruded Plastic Film for packagingand industrial applications. The principal place of business of the company is at
Abrama-
Valsad. Th
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.219 — score 0.570</summary>

```
 Office: National Highway No. 8, Water Works Cross Road, Abrama,  
Valsad- 396001, Gujarat, India, CIN: L25200GJ1981PLC004375,  
Tel: 9879554138, E-mail: investor@ecoplastindia.com 
Website: www.ecoplastindia.com 
 
Form No. MGT-11 
Proxy Form 
[Pursuant to section 105(6) of the Companies Act, 2013 and rule 19(3) of  
the Companies (Management and Administration) Rules, 2014] 
 
Name of the Member(s)___________________________________________________________ 
 
Registered address: ______________
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.70 — score 0.567</summary>

```
 s 
in India, offering a diverse range of bags catering to a wide array of applications. Its 
client base includes numerous MNCs serving the hygiene sector in India. We also have 
exports into the United States and African markets catering to the hospitality and food 
industry respectively. With this merger, all the business and operating entities within 
the group now stand consolidated under Ecoplast Limited.  
 
Increased trade tariffs announced by the USA on India, and the resulting uncertai
```

</details>

---

## q005

**Question:** What was Ecoplast's interest coverage ratio as at 31 March 2026?

**Reference answer:** 37.98

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.138 — score 0.638</summary>

```
2,388 5.86%
As at 31st March, 2026                2,02,388 5.86%
Ecoplast Limited
Particulars
The Paid-up Capital includes 1,500,000 Equity Shares of Rs.10 each allotted as fully paid up Bonus shares by capitalisingRs. 50.00 lacs out of General Reserve and Rs. 100.00 lacs
out of Revaluation Reserve prior to listing of Company 's Equity Shares.
The holders of equity shares will be entitled to receive remaining assets of the Company, after distribution of all preferential amounts in the event of l
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.204 — score 0.626</summary>

```
exposure in forex to mitigate risks to earnings;
Leverage optimally in order to maximum shareholders returns while maintaining strength and flexibility of the balance sheet.
Particulars As at 
31st March, 2026
As at  
31st March, 2025
Notes forming Part of Consolidated Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
The Group’s policy is to maintain a strong capital base so as to ensure that the Group is able to continue as going concern to sustain future development
of
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.147 — score 0.622</summary>

```
 and flexibility of the balance sheet.
Particulars As at 
31st March, 2026
As at  
31st March, 2025
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
The Company’s policy is to maintain a strong capital base so as to ensure that the Company is able to continue as going concern to sustain future
development of the business. The capital structure of the Company isbased on management’s judgement of its strategic and day-to-day needs with a
fo
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.151, 152 — score 0.617</summary>

```
 of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
PVO at the end of the year
147
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
b) Fair value of plan assets: (Rs. Lacs)
31st March, 2026 31st March, 2025
682.74                           648.72                           
Interest income 46.63                              46.84                              
24.05                              23.88    
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.209 — score 0.613</summary>

```
March, 2026 31st March, 2025
Expected Rate on Plan Assets
For Ecoplast Limited : 
7.48%
For Kunal Plastics 
Private Limited : 7.40 
% 6.83%
Rate of Discounting
For Ecoplast Limited : 
7.48%
For Kunal Plastics 
Private Limited : 7.40 
% 6.83%
Rate of Salary Increase
For Ecoplast Limited : 
8%
For Kunal Plastics 
Private Limited : 7%
8% for Ecoplast 
Limited Employees 
and 7% for Kunal 
Plastic Private Limited 
Employees
Rate of Employee Turnover
For Ecoplast Limited : 
3% and For Kunal 
Plastic P
```

</details>

---

## q006

**Question:** What current ratio did Ecoplast report as at 31 March 2026?

**Reference answer:** 3.51

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.147 — score 0.643</summary>

```
 and flexibility of the balance sheet.
Particulars As at 
31st March, 2026
As at  
31st March, 2025
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
The Company’s policy is to maintain a strong capital base so as to ensure that the Company is able to continue as going concern to sustain future
development of the business. The capital structure of the Company isbased on management’s judgement of its strategic and day-to-day needs with a
fo
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.218, 219 — score 0.633</summary>

```
0th May, 2026 Date : 30th May, 2026
The Financial Statements were authorised for issue in accordance with a resolution of the Board of Dire ctors in its meeting held on May 30, 2026.
Previous periods/ years figures have been reworked/regrouped/ reclassified, wherever necessary, to make them comparable with the figures of the current periods / years and after
considering the effect of the merger as stated herein above.
214
ECOPLAST LIMITED 
Regd.  Office: National Highway No. 8, Water Works Cross
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.158 — score 0.625</summary>

```
emen ts for the year ended 31st March, 2026
Ecoplast Limited
36
(Rs. Lacs)
As at 
31st March, 2026
As at  
31st March, 2025
                    32.20                    19.91 
 b) The amount spent during the year on CSR activities is as follows:
1) Construction/Acquisition of any asset                            -                             -   
                    32.20                    19.91 
37 Event occurring after Balance Sheet date:
38 Additional Regulatory Information
1
2
3
4
5
6
7
8
 
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.1, 2, 3 — score 0.622</summary>

```
.ecoplastindia.com 
 
We request you to take the same on record. 
 
Thanking you 
 
Yours faithfully 
For Ecoplast Limited 
 
 
 
Rakesh Kumar Kumawat 
Company Secretary & Compliance Officer 
 
Encl: As above 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
  Ecoplast Limited 
 
 
 
44th Annual Report 2025-26 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
44 
Ecoplast Limited 
 
 Annual Report 2025-26  
   
Board of Directors 
(as on 31.03.2026)
 
B R Tarafdar -  Chairman & Independent Directo
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.151, 152 — score 0.616</summary>

```
 of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
PVO at the end of the year
147
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
b) Fair value of plan assets: (Rs. Lacs)
31st March, 2026 31st March, 2025
682.74                           648.72                           
Interest income 46.63                              46.84                              
24.05                              23.88    
```

</details>

---

## q007

**Question:** Which single business segment does Ecoplast operate in?

**Reference answer:** Plastic Films — its sole business segment.

**Model answer:** Ecoplast operates in the Value-added product business segment.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.66 — score 0.642</summary>

```
a. Ecoplast Ltd. specializes in producing 
high-quality, multilayer coextruded polyethylene and co-polymer films with an 
annual capacity of 9600 MT.  
Since its inception in 1981, the Company had played a major role in the development 
of the flexible packaging industry in India by supplying lamination grade films. 
However, in view of poor margins and fierce competition in the commodity 
lamination business, the company transitioned into only Value-added product 
business. Since 2024 the focus
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.43 — score 0.613</summary>

```
s serving the hygiene sector in India. We also have exports 
into the United States and African markets catering to the hospitality and food industry 
respectively. With this merger, all the business and operating entities within the group 
now stand consolidated under Ecoplast Limited.  
 
Increased trade tariffs announced by the USA on India, and the resulting uncertainty, 
affected export orders and realizations during the year. The Company is responding by 
concentrating its efforts on devel
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.3, 4 — score 0.572</summary>

```
ast), Mumbai- 400069, Maharashtra 
 
Website                           www.ecoplastindia.com 
 
 
CIN                                  L25200GJ1981PLC004375
 T S  
 
 
 
Notice......................................................................................... 01 
                                  
                                Board’s Report…...................................................................... 38 
 
Management Discussion and Analysis Report................. 62 
 
Corpor
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.219 — score 0.568</summary>

```
 Office: National Highway No. 8, Water Works Cross Road, Abrama,  
Valsad- 396001, Gujarat, India, CIN: L25200GJ1981PLC004375,  
Tel: 9879554138, E-mail: investor@ecoplastindia.com 
Website: www.ecoplastindia.com 
 
Form No. MGT-11 
Proxy Form 
[Pursuant to section 105(6) of the Companies Act, 2013 and rule 19(3) of  
the Companies (Management and Administration) Rules, 2014] 
 
Name of the Member(s)___________________________________________________________ 
 
Registered address: ______________
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.70 — score 0.565</summary>

```
 s 
in India, offering a diverse range of bags catering to a wide array of applications. Its 
client base includes numerous MNCs serving the hygiene sector in India. We also have 
exports into the United States and African markets catering to the hospitality and food 
industry respectively. With this merger, all the business and operating entities within 
the group now stand consolidated under Ecoplast Limited.  
 
Increased trade tariffs announced by the USA on India, and the resulting uncertai
```

</details>

---

## q008

**Question:** How did Ecoplast's return on net worth move between 31 March 2025 and 31 March 2026, and what explanation is given?

**Reference answer:** It fell from 0.16 to 0.11, a 32% decline. The company attributes this to fresh equity issued in the previous year, which increased total equity.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.151, 152 — score 0.637</summary>

```
 of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
PVO at the end of the year
147
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
b) Fair value of plan assets: (Rs. Lacs)
31st March, 2026 31st March, 2025
682.74                           648.72                           
Interest income 46.63                              46.84                              
24.05                              23.88    
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.193, 194 — score 0.617</summary>

```
oted)
Investments in Mutual Funds 300.47                            1,806.86                             
Total 300.47                            1,806.86                             
Ecoplast Limited
Notes forming Part of Consolidated Financial Statements for the year ended 31st March, 2026
 (i) The mode of valuation has been stated in Note 1 .9 
 (ii) Inventories have been hypothecated as security for borrowings. 
189
Ecoplast Limited
Notes forming Part of Consolidated Financial Statements for
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.119, 120 — score 0.608</summary>

```
       
(617.14)                        (2,918.45)                      
Net cash flow used in investing activities (B) (617. 14)                       (2,918.45)                      
Ecoplast Limited
Standalone Statement of Cash Flows for the Year ended 31st March 2026
 For the year ended
31st March, 2026 
 For the year ended
31st March, 2025 
CIN - L25200GJ1981PLC004375
Particulars
Audited Audited
115
(Rs. Lacs)
Ecoplast Limited
Standalone Statement of Cash Flows for the Year ended 31st March
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.158 — score 0.604</summary>

```
emen ts for the year ended 31st March, 2026
Ecoplast Limited
36
(Rs. Lacs)
As at 
31st March, 2026
As at  
31st March, 2025
                    32.20                    19.91 
 b) The amount spent during the year on CSR activities is as follows:
1) Construction/Acquisition of any asset                            -                             -   
                    32.20                    19.91 
37 Event occurring after Balance Sheet date:
38 Additional Regulatory Information
1
2
3
4
5
6
7
8
 
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.147 — score 0.600</summary>

```
 and flexibility of the balance sheet.
Particulars As at 
31st March, 2026
As at  
31st March, 2025
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
Ecoplast Limited
The Company’s policy is to maintain a strong capital base so as to ensure that the Company is able to continue as going concern to sustain future
development of the business. The capital structure of the Company isbased on management’s judgement of its strategic and day-to-day needs with a
fo
```

</details>

---

## q009

**Question:** Ecoplast's debtors turnover and inventory turnover moved in opposite directions during 2025-26. What were both ratios at 31 March 2026?

**Reference answer:** Debtors turnover 6.98 (up 1% from 6.90); inventory turnover 5.92 (down 7% from 6.36).

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.136, 137 — score 0.613</summary>

```
ts subsidiary has realised a compensation of INR 110.36 lacs on 10th April 2024. Accordingly,
value of investment has been restated in previous year, by reversing the impairment to the extent of its realisable value.
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
132
Ecoplast Limited
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
6.2 TRADE RECEIVABLES 
 (Rs. Lacs) 
Particulars  As at 
31st March, 2026 
 As at  
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.206 — score 0.605</summary>

```
.94                      105.94                      -                            -                            
Lease liabilities 92.00                        43.76                        48.24                        -                            
1,797.23                  1,748.99                  48.24                        -                            
Ecoplast Limited
Notes forming Part of Consolidated Financial Statements for the year ended 31st March, 2026
Particulars
 As at  31st March, 2
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.193, 194 — score 0.595</summary>

```
oted)
Investments in Mutual Funds 300.47                            1,806.86                             
Total 300.47                            1,806.86                             
Ecoplast Limited
Notes forming Part of Consolidated Financial Statements for the year ended 31st March, 2026
 (i) The mode of valuation has been stated in Note 1 .9 
 (ii) Inventories have been hypothecated as security for borrowings. 
189
Ecoplast Limited
Notes forming Part of Consolidated Financial Statements for
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.158, 159 — score 0.591</summary>

```
Tax Act, 1961.
The Quarterly returns / Statements of current assets filed by the company with the banks in relation to secured borrowings, wherever applicable, are in agreement with the books of
accounts.
154
Notes Forming Part of Standalone Financial Statemen ts for the year ended 31st March, 2026
Ecoplast Limited
39
Current Year Previous Year % of Variance Reasons for 
Variances
3.51 4.57 -23% Below threshold of 25%
0.01 0.00 0% Below threshold of 25%
31.14 4.45 600%
Complete borrowings
repaid
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.143, 144 — score 0.589</summary>

```
92                       
Staff Welfare expenses 29.36                         25.07                         
Total 2,738.05                   2,357.38                   
139
 
Ecoplast Limited
Notes Forming Part of Standalone Financial Statements for the year ended 31st March, 2026
21 FINANCE COSTS
 (Rs. Lacs) 
Particulars
 For the year ended
31st March, 2026 
 For the year ended
31st March, 2025 
Interest expense 20.85                         51.52                         
Other Borrowing cost
```

</details>

---

## q010

**Question:** Which two external disruptions does Ecoplast say hit its business during the year, and what is it doing about each?

**Reference answer:** (1) Higher US trade tariffs on India hurt export orders and realizations — the company is developing new customers in other export markets. (2) Escalating conflict in West Asia in the final quarter disrupted raw material availability and pricing — the company is securing its raw material supply chains.

**Model answer:** Ecoplast cites increased trade tariffs announced by the USA on India and resulting uncertainty as disruptions that affected its business. The company is responding by concentrating its efforts on developing solutions to address these challenges.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] ecoplast_2025_26_annual_report.pdf p.43 — score 0.549</summary>

```
s serving the hygiene sector in India. We also have exports 
into the United States and African markets catering to the hospitality and food industry 
respectively. With this merger, all the business and operating entities within the group 
now stand consolidated under Ecoplast Limited.  
 
Increased trade tariffs announced by the USA on India, and the resulting uncertainty, 
affected export orders and realizations during the year. The Company is responding by 
concentrating its efforts on devel
```

</details>
<details><summary>[2] ecoplast_2025_26_annual_report.pdf p.66 — score 0.548</summary>

```
a. Ecoplast Ltd. specializes in producing 
high-quality, multilayer coextruded polyethylene and co-polymer films with an 
annual capacity of 9600 MT.  
Since its inception in 1981, the Company had played a major role in the development 
of the flexible packaging industry in India by supplying lamination grade films. 
However, in view of poor margins and fierce competition in the commodity 
lamination business, the company transitioned into only Value-added product 
business. Since 2024 the focus
```

</details>
<details><summary>[3] ecoplast_2025_26_annual_report.pdf p.1, 2, 3 — score 0.505</summary>

```
.ecoplastindia.com 
 
We request you to take the same on record. 
 
Thanking you 
 
Yours faithfully 
For Ecoplast Limited 
 
 
 
Rakesh Kumar Kumawat 
Company Secretary & Compliance Officer 
 
Encl: As above 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
  Ecoplast Limited 
 
 
 
44th Annual Report 2025-26 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
44 
Ecoplast Limited 
 
 Annual Report 2025-26  
   
Board of Directors 
(as on 31.03.2026)
 
B R Tarafdar -  Chairman & Independent Directo
```

</details>
<details><summary>[4] ecoplast_2025_26_annual_report.pdf p.70 — score 0.505</summary>

```
 s 
in India, offering a diverse range of bags catering to a wide array of applications. Its 
client base includes numerous MNCs serving the hygiene sector in India. We also have 
exports into the United States and African markets catering to the hospitality and food 
industry respectively. With this merger, all the business and operating entities within 
the group now stand consolidated under Ecoplast Limited.  
 
Increased trade tariffs announced by the USA on India, and the resulting uncertai
```

</details>
<details><summary>[5] ecoplast_2025_26_annual_report.pdf p.47, 48 — score 0.504</summary>

```
on the website of the Company at 
www.ecoplastindia.com. 
 
ANNUAL RETURN: 
Pursuant to Section 92(3) and 134(3)(a) of the Act and the Companies (Management and 
Administration) Rules, 2014, the Annual Return for FY 25-26 is available on the website 
of the Company at www.ecoplastindia.com. 
 
 
43
  
AUDITORS:  
As per the provisions of Section 139 of the Act read with the Companies (Audit and 
Auditors) Rules, 2014, M/s. Y.B. Desai & Associates, Chartered Accountants, Surat, 
(ICAI Registratio
```

</details>

---

## q011

**Question:** What did Goa Carbon earn in sales and other income during 2025-26?

**Reference answer:** ₹70,879.78 lakhs.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] goa_carbon_2025_26_annual_report.pdf p.81 — score 0.683</summary>

```
s of Goa Carbon Limited
Report on the audit of the Annual Financial 
Results
Opinion
We have audited the accompanying annual financial results of 
Goa Carbon Limited (hereinafter referred to as the “Company”) 
for the year ended 31 March 2026, attached herewith, being 
submitted by the Company pursuant to the requirement of 
Regulation 33 of the Securities and Exchange Board of India 
(Listing Obligations and Disclosure Requirements) Regulations, 
2015, as amended ("Listing Regulations").
In our
```

</details>
<details><summary>[2] goa_carbon_2025_26_annual_report.pdf p.89, 90 — score 0.672</summary>

```
cutive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 26133124ADOMGJ2064
 Vikrant Garg  Pravin R. Satardekar
Place : Panaji, Goa Chief Financial Officer Company Secretary
Dated : 7th May, 2026 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
86
NOTES TO THE FINANCIAL STATEMENTS
for the year ended 31 st March 2026
1 Company overview
  Goa Carbon Limited is a public limited company 
incorporated and dom
```

</details>
<details><summary>[3] goa_carbon_2025_26_annual_report.pdf p.71 — score 0.665</summary>

```
audited the financial statements of Goa Carbon Limited 
(the “Company”) which comprise the balance sheet as at 31 
March 2026, and the statement of profit and loss (including 
other comprehensive income), statement of changes in equity 
and statement of cash flows for the year then ended, and notes 
to the financial statements, including material accounting 
policies and other explanatory information.
In our opinion and to the best of our information and according 
to the explanations given to u
```

</details>
<details><summary>[4] goa_carbon_2025_26_annual_report.pdf p.89 — score 0.662</summary>

```
75.38 1,803.05  9,982.25  556.17  15,947.86 
 Summary of material accounting policies   2 - 3
 The accompanying notes to the financial statements. 4 - 48
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No.
```

</details>
<details><summary>[5] goa_carbon_2025_26_annual_report.pdf p.83, 84 — score 0.661</summary>

```
6 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
80
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 
```

</details>

---

## q012

**Question:** How much calcined petroleum coke did Goa Carbon manufacture in 2025-26?

**Reference answer:** 1,34,585 MT.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] goa_carbon_2025_26_annual_report.pdf p.42 — score 0.670</summary>

```
ty, and strong environmental practices to strengthen their 
long-term competitiveness.
Sources: Ministry of Mines, Government of India - Annual Report FY26, 
IEA - Global Energy Review 2026, IEA - Aluminium, IAI - Aluminium 
Sector Greenhouse Gas Pathways to 2050
Company Overview
Goa Carbon Limited (‘GCL’ or ‘the Company’), the manufacturing 
flagship of the Dempo Group, is one of India’s leading 
manufacturers of Calcined Petroleum Coke (CPC). Since its 
establishment in 1967, the Company has b
```

</details>
<details><summary>[2] goa_carbon_2025_26_annual_report.pdf p.90 — score 0.659</summary>

```
 is a public limited company 
incorporated and domiciled in India and has its registered 
office at Dempo House Campal Panaji-Goa, India - 403001.
  The Company is in the business of manufacture and sale 
of Calcined Petroleum Coke (CPC) from its manufacturing 
facilities at Goa, Paradeep and Bilaspur. The Company’s 
shares are listed on Bombay Stock Exchange (BSE) and 
National Stock Exchange (NSE).
2  Basis of preparation of financial 
statements
 a.  Basis of preparation and compliance 
with 
```

</details>
<details><summary>[3] goa_carbon_2025_26_annual_report.pdf p.89 — score 0.610</summary>

```
75.38 1,803.05  9,982.25  556.17  15,947.86 
 Summary of material accounting policies   2 - 3
 The accompanying notes to the financial statements. 4 - 48
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No.
```

</details>
<details><summary>[4] goa_carbon_2025_26_annual_report.pdf p.42 — score 0.605</summary>

```
ince its 
establishment in 1967, the Company has been engaged in 
converting Raw Petroleum Coke (RPC), a by-product of the 
petroleum refining process, into value-added CPC or blending 
thereof, an essential raw material for the aluminium, steel, 
graphite, titanium dioxide, and refractory industries.
With strategically located manufacturing facilities in Goa, 
Paradeep (Odisha), and Bilaspur (Chhattisgarh), GCL has 
established a robust manufacturing and distribution network 
that enables it to
```

</details>
<details><summary>[5] goa_carbon_2025_26_annual_report.pdf p.83, 84 — score 0.599</summary>

```
6 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
80
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 
```

</details>

---

## q013

**Question:** What loss before tax did Goa Carbon report for 2025-26?

**Reference answer:** A loss of ₹4,211.61 lakhs.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] goa_carbon_2025_26_annual_report.pdf p.81 — score 0.659</summary>

```
s of Goa Carbon Limited
Report on the audit of the Annual Financial 
Results
Opinion
We have audited the accompanying annual financial results of 
Goa Carbon Limited (hereinafter referred to as the “Company”) 
for the year ended 31 March 2026, attached herewith, being 
submitted by the Company pursuant to the requirement of 
Regulation 33 of the Securities and Exchange Board of India 
(Listing Obligations and Disclosure Requirements) Regulations, 
2015, as amended ("Listing Regulations").
In our
```

</details>
<details><summary>[2] goa_carbon_2025_26_annual_report.pdf p.89 — score 0.657</summary>

```
75.38 1,803.05  9,982.25  556.17  15,947.86 
 Summary of material accounting policies   2 - 3
 The accompanying notes to the financial statements. 4 - 48
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No.
```

</details>
<details><summary>[3] goa_carbon_2025_26_annual_report.pdf p.71 — score 0.647</summary>

```
audited the financial statements of Goa Carbon Limited 
(the “Company”) which comprise the balance sheet as at 31 
March 2026, and the statement of profit and loss (including 
other comprehensive income), statement of changes in equity 
and statement of cash flows for the year then ended, and notes 
to the financial statements, including material accounting 
policies and other explanatory information.
In our opinion and to the best of our information and according 
to the explanations given to u
```

</details>
<details><summary>[4] goa_carbon_2025_26_annual_report.pdf p.83 — score 0.640</summary>

```
31 62.10
(d) Current tax liabilities (net) 25 - -
Total current liabilities 20,148.10 31,346.04
Total Liabilities 20,148.10 31,346.04
TOTAL EQUITY AND LIABILITIES 37,011.07 53,107.10
Summary of material accounting policies        2 - 3
The accompanying notes to the financial statements.     4 - 48
The notes referred to above form an integral part of financial statements.
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited

```

</details>
<details><summary>[5] goa_carbon_2025_26_annual_report.pdf p.83, 84 — score 0.636</summary>

```
6 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
80
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 
```

</details>

---

## q014

**Question:** Why did Goa Carbon pay no dividend for the year ended 31 March 2026?

**Reference answer:** Because of the losses it incurred. Directors recommended no dividend, and no amount was transferred to reserve.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] goa_carbon_2025_26_annual_report.pdf p.71 — score 0.672</summary>

```
audited the financial statements of Goa Carbon Limited 
(the “Company”) which comprise the balance sheet as at 31 
March 2026, and the statement of profit and loss (including 
other comprehensive income), statement of changes in equity 
and statement of cash flows for the year then ended, and notes 
to the financial statements, including material accounting 
policies and other explanatory information.
In our opinion and to the best of our information and according 
to the explanations given to u
```

</details>
<details><summary>[2] goa_carbon_2025_26_annual_report.pdf p.81 — score 0.666</summary>

```
s of Goa Carbon Limited
Report on the audit of the Annual Financial 
Results
Opinion
We have audited the accompanying annual financial results of 
Goa Carbon Limited (hereinafter referred to as the “Company”) 
for the year ended 31 March 2026, attached herewith, being 
submitted by the Company pursuant to the requirement of 
Regulation 33 of the Securities and Exchange Board of India 
(Listing Obligations and Disclosure Requirements) Regulations, 
2015, as amended ("Listing Regulations").
In our
```

</details>
<details><summary>[3] goa_carbon_2025_26_annual_report.pdf p.1 — score 0.662</summary>

```
ebsite: www.goacarbon.com  
Corporate Identity Number - L23109GA1967PLC000076 
Company Scrip Code / Symbol: 509567 / GOACARBON 	 " ISIN Code: INE426D01013 
Ref. No.: 20261V11113 	
1 1 th August 2026 
Sub.: Submission of 58th Annual Report for the Financial Year 2025-26 and Notice convening the 
58th Annual General Meeting 	 AGM') of Goa Carbon Limited (`the Company')  
Dear Sir(s), 
Pursuant to Regulation 34(1) of the SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015 
(`SE
```

</details>
<details><summary>[4] goa_carbon_2025_26_annual_report.pdf p.89, 90 — score 0.658</summary>

```
cutive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 26133124ADOMGJ2064
 Vikrant Garg  Pravin R. Satardekar
Place : Panaji, Goa Chief Financial Officer Company Secretary
Dated : 7th May, 2026 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
86
NOTES TO THE FINANCIAL STATEMENTS
for the year ended 31 st March 2026
1 Company overview
  Goa Carbon Limited is a public limited company 
incorporated and dom
```

</details>
<details><summary>[5] goa_carbon_2025_26_annual_report.pdf p.83, 84 — score 0.630</summary>

```
6 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
80
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 
```

</details>

---

## q015

**Question:** What is the face value of one Goa Carbon equity share?

**Reference answer:** ₹10.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] sumit_2025_26_annual_report.pdf p.241 — score 0.583</summary>

```
.25 2,500 0.25 
(Equity Shares of the face value of ₹ 10/- 
each fully paid-up)
       
Goa Urban Bank Share Money* 5 -   5 -   
(Equity Shares of the face value of ₹ 10/- 
each fully paid-up)
       
Total investments   0.25   0.25 
         
Aggregate book value of quoted 
investments
  -      -    
Aggregate market value of quoted 
investments
  -      -    
Aggregate carrying value of unquoted 
investments
  0.25   0.25 
Aggregate amount of impairment 
in value of investments in Limited 
Lia
```

</details>
<details><summary>[2] sumit_2025_26_annual_report.pdf p.151, 152 — score 0.571</summary>

```
Bank Shares 2,500 0.25 2,500 0.25 
  (Equity Shares of the face value of ₹ 10/- 
each fully paid-up)
       
  Goa Urban Bank Share Money* 5 -   5 -   
  (Equity Shares of the face value of ₹ 10/- 
each fully paid-up)
       
  Total investments   0.25   0.25 
           
  Aggregate book value of quoted 
investments
  -     -   
  Aggregate market value of quoted 
investments
  -     -   
153
Sumit Woods Limited
Notes forming part of the Standalone financial statements
All amounts are ₹ in Lakh
```

</details>
<details><summary>[3] goa_carbon_2025_26_annual_report.pdf p.10, 11 — score 0.568</summary>

```
-10454,  
CP-7853, PR-1775/2022
Investor Information
Market Capitalisation: ₹253.39 Crore  
(as of 31st March 2026)
BSE Code: 509567  
NSE Symbol: GOACARBON  
AGM Date: 9 th September 2026
AGM Mode: Video Conferencing  
(VC) / Other Audio Visual Means (OAVM)
Website
www.goacarbon.com
www.dempos.com
07
Corporate Overview

NOTICE
(Pursuant to Section 101 of the Companies Act, 2013)
Dear Member,
Notice is hereby given that the Fifty-eight Annual General Meeting (AGM / 58 th AGM) of the Members of G
```

</details>
<details><summary>[4] goa_carbon_2025_26_annual_report.pdf p.1 — score 0.565</summary>

```
ebsite: www.goacarbon.com  
Corporate Identity Number - L23109GA1967PLC000076 
Company Scrip Code / Symbol: 509567 / GOACARBON 	 " ISIN Code: INE426D01013 
Ref. No.: 20261V11113 	
1 1 th August 2026 
Sub.: Submission of 58th Annual Report for the Financial Year 2025-26 and Notice convening the 
58th Annual General Meeting 	 AGM') of Goa Carbon Limited (`the Company')  
Dear Sir(s), 
Pursuant to Regulation 34(1) of the SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015 
(`SE
```

</details>
<details><summary>[5] sayaji_2025_26_annual_report.pdf p.31, 32 — score 0.552</summary>

```
 
30,46,605 Equity Shares of Face Value INR 10/- (Indian Rupees Ten Only) each. 
 
During the year under review, the Company had not issued shares with differential 
voting right neither granted stock option nor sweat equity. Further the Company had  
not issued any debenture bonds and any nonconvertible securities. 
 
The Company’s equity shares are listed with the Bombay Stock Exchange i.e. BSE 
Limited and the ISIN of the Company is “INE07G501017”.  
 
21
 
DIVIDEND  
 
In order to conserve c
```

</details>

---

## q016

**Question:** Goa Carbon paid nothing to shareholders in 2025-26. What had it paid the year before, and what did that cost?

**Reference answer:** ₹10.00 per equity share as the final dividend for the year ended 31 March 2024, a cash outflow of ₹915.11 lakhs.

**Model answer:** Goa Carbon paid 2,338.73 in the year 2025-26, and it had paid 1,806.44 the year before.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] goa_carbon_2025_26_annual_report.pdf p.87 — score 0.673</summary>

```
e year 2,338.73 1,806.44
Amount paid during the year (2,338.73) (1,806.44)
Closing balance - -
Summary of material accounting policies   2 - 3
The accompanying notes to the financial statements 4 - 48
STATEMENT OF CASH FLOWS (Continued)
for the year ended 31 st March 2026
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Kha
```

</details>
<details><summary>[2] goa_carbon_2025_26_annual_report.pdf p.89 — score 0.664</summary>

```
75.38 1,803.05  9,982.25  556.17  15,947.86 
 Summary of material accounting policies   2 - 3
 The accompanying notes to the financial statements. 4 - 48
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No.
```

</details>
<details><summary>[3] goa_carbon_2025_26_annual_report.pdf p.71 — score 0.651</summary>

```
audited the financial statements of Goa Carbon Limited 
(the “Company”) which comprise the balance sheet as at 31 
March 2026, and the statement of profit and loss (including 
other comprehensive income), statement of changes in equity 
and statement of cash flows for the year then ended, and notes 
to the financial statements, including material accounting 
policies and other explanatory information.
In our opinion and to the best of our information and according 
to the explanations given to u
```

</details>
<details><summary>[4] goa_carbon_2025_26_annual_report.pdf p.81 — score 0.648</summary>

```
s of Goa Carbon Limited
Report on the audit of the Annual Financial 
Results
Opinion
We have audited the accompanying annual financial results of 
Goa Carbon Limited (hereinafter referred to as the “Company”) 
for the year ended 31 March 2026, attached herewith, being 
submitted by the Company pursuant to the requirement of 
Regulation 33 of the Securities and Exchange Board of India 
(Listing Obligations and Disclosure Requirements) Regulations, 
2015, as amended ("Listing Regulations").
In our
```

</details>
<details><summary>[5] goa_carbon_2025_26_annual_report.pdf p.89, 90 — score 0.635</summary>

```
cutive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 26133124ADOMGJ2064
 Vikrant Garg  Pravin R. Satardekar
Place : Panaji, Goa Chief Financial Officer Company Secretary
Dated : 7th May, 2026 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
86
NOTES TO THE FINANCIAL STATEMENTS
for the year ended 31 st March 2026
1 Company overview
  Goa Carbon Limited is a public limited company 
incorporated and dom
```

</details>

---

## q017

**Question:** How did Goa Carbon's gearing change over 2025-26, and what were total debt and total equity at the year end?

**Reference answer:** The debt-equity ratio fell from 1.29 to 0.99, down 23%. At 31 March 2026 total debt was ₹16,740.25 lakhs and total equity ₹16,862.97 lakhs.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] goa_carbon_2025_26_annual_report.pdf p.83 — score 0.702</summary>

```
31 62.10
(d) Current tax liabilities (net) 25 - -
Total current liabilities 20,148.10 31,346.04
Total Liabilities 20,148.10 31,346.04
TOTAL EQUITY AND LIABILITIES 37,011.07 53,107.10
Summary of material accounting policies        2 - 3
The accompanying notes to the financial statements.     4 - 48
The notes referred to above form an integral part of financial statements.
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited

```

</details>
<details><summary>[2] goa_carbon_2025_26_annual_report.pdf p.81 — score 0.677</summary>

```
s of Goa Carbon Limited
Report on the audit of the Annual Financial 
Results
Opinion
We have audited the accompanying annual financial results of 
Goa Carbon Limited (hereinafter referred to as the “Company”) 
for the year ended 31 March 2026, attached herewith, being 
submitted by the Company pursuant to the requirement of 
Regulation 33 of the Securities and Exchange Board of India 
(Listing Obligations and Disclosure Requirements) Regulations, 
2015, as amended ("Listing Regulations").
In our
```

</details>
<details><summary>[3] goa_carbon_2025_26_annual_report.pdf p.89 — score 0.677</summary>

```
75.38 1,803.05  9,982.25  556.17  15,947.86 
 Summary of material accounting policies   2 - 3
 The accompanying notes to the financial statements. 4 - 48
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No.
```

</details>
<details><summary>[4] goa_carbon_2025_26_annual_report.pdf p.89, 90 — score 0.675</summary>

```
cutive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 26133124ADOMGJ2064
 Vikrant Garg  Pravin R. Satardekar
Place : Panaji, Goa Chief Financial Officer Company Secretary
Dated : 7th May, 2026 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
86
NOTES TO THE FINANCIAL STATEMENTS
for the year ended 31 st March 2026
1 Company overview
  Goa Carbon Limited is a public limited company 
incorporated and dom
```

</details>
<details><summary>[5] goa_carbon_2025_26_annual_report.pdf p.71 — score 0.665</summary>

```
audited the financial statements of Goa Carbon Limited 
(the “Company”) which comprise the balance sheet as at 31 
March 2026, and the statement of profit and loss (including 
other comprehensive income), statement of changes in equity 
and statement of cash flows for the year then ended, and notes 
to the financial statements, including material accounting 
policies and other explanatory information.
In our opinion and to the best of our information and according 
to the explanations given to u
```

</details>

---

## q018

**Question:** What debt service coverage ratio did Goa Carbon report for 2025-26, and what reason is given for the change?

**Reference answer:** (0.67), against (0.41) the previous year — a 62% change. The company attributes the reduction mainly to operational losses incurred during the current financial year.

**Model answer:** I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] goa_carbon_2025_26_annual_report.pdf p.81 — score 0.629</summary>

```
s of Goa Carbon Limited
Report on the audit of the Annual Financial 
Results
Opinion
We have audited the accompanying annual financial results of 
Goa Carbon Limited (hereinafter referred to as the “Company”) 
for the year ended 31 March 2026, attached herewith, being 
submitted by the Company pursuant to the requirement of 
Regulation 33 of the Securities and Exchange Board of India 
(Listing Obligations and Disclosure Requirements) Regulations, 
2015, as amended ("Listing Regulations").
In our
```

</details>
<details><summary>[2] goa_carbon_2025_26_annual_report.pdf p.71 — score 0.628</summary>

```
audited the financial statements of Goa Carbon Limited 
(the “Company”) which comprise the balance sheet as at 31 
March 2026, and the statement of profit and loss (including 
other comprehensive income), statement of changes in equity 
and statement of cash flows for the year then ended, and notes 
to the financial statements, including material accounting 
policies and other explanatory information.
In our opinion and to the best of our information and according 
to the explanations given to u
```

</details>
<details><summary>[3] sayaji_2025_26_annual_report.pdf p.176 — score 0.623</summary>

```
lted in Improvement in ratio.
23.88% -10.89%
4 Debt Service Coverage Ratio
Earning for Debt 
Service = Net Profit 
after taxes 
+ Non-cash operating 
expenses + Interest + 
Other non-cash 
adjustments
Debt service = Interest 
and lease payments + 
Principal repayments
Times 11.63 1281.74%
14.61
-  
-  
14.61
CSR Initiatives Related To The
Environment
For the year ended 31st March, 2025 For the year ended 31st March, 2026
(Amount In Rs. Lakhs)
As per Section 135 of the Companies Act, 2013, a comp
```

</details>
<details><summary>[4] goa_carbon_2025_26_annual_report.pdf p.83, 84 — score 0.621</summary>

```
6 M.No.: ACA - 508132  M.No.: ACS - 24380
 Place : Panaji, Goa
 Dated : 7th May, 2026
Annual Report 2025-26
80
As per our report of even date attached
For B S R & Co. LLP For and on behalf of the Board of Directors of Goa Carbon Limited
Chartered Accountants (CIN: L23109GA1967PLC000076)
Firm Registration No. 101248W/W-100022
Kalpesh Khandelwal Shrinivas V. Dempo Anupam Misra
Partner  Chairman and Non Executive Director  Executive Director
Membership No. 133124 DIN: 00043413  DIN: 09615362
UDIN: 
```

</details>
<details><summary>[5] goa_carbon_2025_26_annual_report.pdf p.65, 66 — score 0.619</summary>

```
09615362
Place: Panaji, Goa
Date: 27th April 2026
Annual Report 2025-26
62
CEO/CFO CERTIFICATION IN RESPECT OF FINANCIAL STATEMENTS AND CASH FLOW STATEMENT 
(PURSUANT TO REGULATION 17(8) OF SEBI (LISTING OBLIGATIONS & DISCLOSURE REQUIREMENTS), 
REGULATIONS, 2015 FOR THE PERIOD ENDED 31st MARCH 2026
To,
The Board of Directors
GOA CARBON LIMITED
We, Anupam Misra, Executive Director and Vikrant Garg, Chief Financial Officer of Goa Carbon Limited (“the Company), to the 
best of our knowledge and bel
```

</details>

---

## q019

**Question:** What basic earnings per share did Infosys report on a consolidated basis for fiscal 2026?

**Reference answer:** ₹71.58.

**Model answer:** The basic earnings per share reported by Infosys on a consolidated basis for fiscal 2026 is ` 71.58.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] infosys_2025_26_annual_report.pdf p.287, 288 — score 0.714</summary>

```
or the year   32 , 811  27, 209 
Infosys Integrated Annual Report 2025-26
319
Particulars Note Year ended March 31,
2026 2025
Profit attributable to:    
Owners of the Company   29,440  26,713 
Non-controlling interests   34  37 
   29,474  26,750 
Total comprehensive income attributable to:    
Owners of the Company   32,750  27,167 
Non-controlling interests   61  42 
   32 , 811  27, 209 
Earnings per equity share    
Equity shares of par value ` 5/- each    
Basic (`) 2.23  71.58  64.50 
Dil
```

</details>
<details><summary>[2] infosys_2025_26_annual_report.pdf p.322, 323 — score 0.695</summary>

```
 
Special dividend for fiscal 2024  –  8.00 
Final dividend for fiscal 2024  –  20.00 
Infosys Integrated Annual Report 2025-26
354
During the year ended March 31, 2026, on account of the final dividend for fiscal 2025 and interim dividend for fiscal 2026, the Company 
has incurred a net cash outflow of ` 18,653 crore (excluding dividend paid on treasury shares).
The Board of Directors in their meeting held on April 23, 2026 recommended a final dividend of ` 25/-per equity share for the financia
```

</details>
<details><summary>[3] infosys_2025_26_annual_report.pdf p.33, 34 — score 0.695</summary>

```
e and consolidated basis for the year ended March 31, 2026.
(3) Excluding the effect of Income Tax orders received under Sections 250 and 254 of the Income-tax Act, 1961 and The Labour Codes provisions notified by the 
Government of India, Diluted EPS increase (in ` terms) is 16.0% and 12.2% YoY on standalone and consolidated basis for the year ended March 31, 2026.
Board's report
Statutory reports
Infosys Integrated Annual Report 2025-26
65
Financial position
(In ` crore)
Particulars Standalone
```

</details>
<details><summary>[4] infosys_2025_26_annual_report.pdf p.343, 344 — score 0.694</summary>

```
es are determined independently 
for each period presented.
Infosys Integrated Annual Report 2025-26
375
The number of equity shares and potentially dilutive equity 
shares are adjusted retrospectively for all periods presented for 
any share splits and bonus shares issues including for changes 
effected prior to the approval of the financial statements by 
the Board of Directors.
The computation of basic earnings per equity share is as follows:
Particulars Year ended March 31,
2026 2025
Profit 
```

</details>
<details><summary>[5] infosys_2025_26_annual_report.pdf p.26 — score 0.687</summary>

```
parency are top priorities in our 
relationship with our investors.
We are privileged to share a strong 
relationship with investors, based 
on a deep understanding of their 
expectations and our commitment to 
creating value for them. Infosys aims 
Basic earnings per share
Dividend per share Free cash flows 
Market capitalization 
Return on Equity 
Revenue growth 
In ` crore
2024
 6,21,821
2025
 6,52,332
2026
5,07,192 In %
4.7
2024
6.1
2025
9.6
2026
In ` 71.58
2026
64.50
2025
63.39
2024
71.58
2
```

</details>

---

## q020

**Question:** What was the Infosys operating margin on a consolidated basis in fiscal 2026?

**Reference answer:** 20.3%.

**Model answer:** The Infosys operating margin on a consolidated basis in fiscal 2026 was 25.3%.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] infosys_2025_26_annual_report.pdf p.77, 78 — score 0.657</summary>

```
ncy grew by 3.1%.
We added 443 new customers (gross) during fiscal 2026 as 
compared to 365 new customers (gross) during fiscal 2025.
Management’s discussion and analysis
Infosys Integrated Annual Report 2025-26
109
On a consolidated basis, for the year ended March 31, 2026, 
approximately 97.1% were export revenues whereas 2.9% were 
domestic revenues, while for the year ended March 31, 2025, 
2. Expenditure
The following table gives an overview of the standalone and consolidated operating expe
```

</details>
<details><summary>[2] infosys_2025_26_annual_report.pdf p.52, 53 — score 0.641</summary>

```

`94.84
– 100 241 141 – 583 35 7 28  100 
Infosys Integrated Annual Report 2025-26
84
(1) Converted at monthly average exchange rates
(2) Wholly-owned subsidiary of Infosys Limited
(3) Majority-owned and controlled subsidiary of Infosys Limited
(4) Wholly-owned subsidiary of Brilliant Basics Holding Limited
(5) Wholly-owned subsidiary of Infosys BPM Limited
(6) Wholly-owned subsidiary of Infosys Consulting Holding AG
(7) Wholly-owned subsidiary of Stater N.V. 
(8) Wholly-owned subsidiary of Info
```

</details>
<details><summary>[3] infosys_2025_26_annual_report.pdf p.46 — score 0.635</summary>

```
Integrated Annual Report 2025-26
77
Sl. 
No.
Name of the 
subsidiary
Country Financial 
period 
ended 
Date of 
acquisition
Exchange 
rate/
Reporting 
currency
Share 
capital
Reserves 
and 
surplus 
Total 
assets
Total 
liabilities 
(excluding 
share 
capital and 
reserves 
and surplus)
Investments Turnover(1) 
(includes 
inter-
company 
transactions)
Profit / 
(Loss) 
before 
taxation(1) 
Provision 
for 
taxation(1) 
Profit / 
(Loss) 
after 
taxation(1) 
% of 
shareholding
11 Infosys 
Consultin
```

</details>
<details><summary>[4] infosys_2025_26_annual_report.pdf p.80 — score 0.629</summary>

```
al operating margin (%) 
2026 25.3 22.1 25.1 30.7 17.7 23.1 20.0 14.8 23.7
2025 24.6 19.3 28.1 32.3 17. 5 24.6 22.5 17. 2 24.1
Overall segment profitability has decreased primarily on account of lower utilization; and investments in talent, AI, sales & marketing, 
which was partially offset by benefits arising from increased realization through pricing and productivity, improved onsite mix and 
foreign currency translation.
The following graph sets forth our revenue by geography:
(In ₹ crore)
 %
```

</details>
<details><summary>[5] infosys_2025_26_annual_report.pdf p.48 — score 0.629</summary>

```
nfosys Integrated Annual Report 2025-26
79
Sl. 
No.
Name of the 
subsidiary
Country Financial 
period 
ended 
Date of 
acquisition
Exchange 
rate/
Reporting 
currency
Share 
capital
Reserves 
and 
surplus 
Total 
assets
Total 
liabilities 
(excluding 
share 
capital and 
reserves 
and surplus)
Investments Turnover(1) 
(includes 
inter-
company 
transactions)
Profit / 
(Loss) 
before 
taxation(1) 
Provision 
for 
taxation(1) 
Profit / 
(Loss) 
after 
taxation(1) 
% of 
shareholding
36 Infosys BPO
```

</details>

---

## q021

**Question:** How many clients did Infosys win during fiscal 2026, and how large was its client base at year end?

**Reference answer:** 443 new clients were added; the total client base stood at 1,965.

**Model answer:** Infosys did not win any clients during fiscal 2026; its client base at the end of the year stood at 1,965.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] infosys_2025_26_annual_report.pdf p.88 — score 0.711</summary>

```
porations. Our total client base at the end of the year stood 
at 1,965. The client segmentation, based on the last 12 months’ 
revenue for the current and previous years, on a consolidated 
basis, is as follows:
Clients 2026 2025
100 million dollar + 41 39
50 million dollar + 88 85
10 million dollar + 328 309
1 million dollar + 1,018 992
5. Infosys Leadership Institute (ILI)
As artificial intelligence continues to redefine enterprise 
priorities, the Infosys Leadership Institute (ILI) plays a p
```

</details>
<details><summary>[2] infosys_2025_26_annual_report.pdf p.88, 89 — score 0.648</summary>

```
d with 
over 1,000 clients and created over 2,000 assets since inception. 
For more information, visit https://infosys.com/iki.
Infosys Integrated Annual Report 2025-26
120
7. ESG vision and ambitions
In October 2020, we launched our ESG Vision 2030 to ‘shape and 
share solutions that serve the development of businesses and 
communities.’ Our vision continues to reflect our commitment 
to responsible business. In fiscal 2025, at the mid-point of 
our journey towards our 2030 goals, we had an opp
```

</details>
<details><summary>[3] infosys_2025_26_annual_report.pdf p.271, 272 — score 0.646</summary>

```
mited  956  1,001 
Infosys Public Services  682  659 
Infosys Compaz Pte Ltd  171  160 
Infosys Consulting Ltda  1 –
Simplus Australia Pty Ltd  1  2 
Infosys Chile SpA  5  7 
Blue Acorn iCi Inc –  2 
Portland Group Pty Ltd  3 –
Kaleidoscope Animations, Inc. –  1 
Infosys Singapore Pte. Ltd.  1 –
Infosys Integrated Annual Report 2025-26
303
Particulars
Year ended March 31, 
2026 2025
BASE life science A/S  15  14 
BASE life science GmbH –  1 
Infosys Business Solutions LLC  13 –
Infosys South Afr
```

</details>
<details><summary>[4] infosys_2025_26_annual_report.pdf p.9, 10 — score 0.639</summary>

```
 medium and long-term value is created 
and preserved at Infosys. The capitals are simultaneously inter-dependent and mutually beneficial as they create 
synergy across the organization. Our strategy, ESG vision and ambitions help to channel all inputs through the capitals 
to manifest into the most impactful outputs and outcomes for all stakeholders.
About Infosys
Corporate overview
3,28,594
Employees
1,965
Active clients 
`1,78,650 cr 
Total revenues in fiscal 2026
Since we refreshed our ESG V
```

</details>
<details><summary>[5] infosys_2025_26_annual_report.pdf p.269, 270 — score 0.637</summary>

```
echnology Private 
Limited –  16 
EdgeVerve Systems Limited  416  293 
Infy Consulting Company Limited –  15 
Infosys South Africa (Pty) Ltd –  5 
Infosys Sweden –  5 
Infosys Compaz Pte Ltd  1  6 
Infosys McCamish Systems LLC  35  7 
Infosys Green Forum  6  2 
GuideVision Deutschland GmbH –  1 
Infosys Middle East FZ LLC  8 –
BASE life science A/S  5  2 
Infosys Integrated Annual Report 2025-26
301
Particulars As at March 31, 
2026 2025
Infosys Consulting GmbH –  1 
Insemi Technology Service Pr
```

</details>

---

## q022

**Question:** How many fresh graduates finished training at the Infosys campus in Mysuru during fiscal 2026?

**Reference answer:** 10,766.

**Model answer:** 10,766 fresh graduates completed the training at the Global Education Center (GEC) campus, Mysuru during fiscal 2026.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] infosys_2025_26_annual_report.pdf p.85 — score 0.622</summary>

```
level hires to transform into corporate professionals. 
Comprising over 40+ technology streams, the curriculum has 
kept pace with the dynamic business requirements and the 
preferred pedagogical approach of the current generation of 
talent. Generative AI and prompt engineering courses have been 
introduced to ensure freshers are adept in the new skills fiscal 
2026, 10,766 fresh graduates completed the training at the Global 
Education Center (GEC) campus, Mysuru and were released to 
delivery
```

</details>
<details><summary>[2] infosys_2025_26_annual_report.pdf p.84, 85 — score 0.610</summary>

```
had taken a career break. 
We were able to hire 947 women into the Infosys ecosystem in 
Fiscal 2026 through this successful endeavor.
During fiscal 2026, we received 58,84,480 employment 
applications, interviewed 4,50,901 applicants and extended 
offers of employment to 87,286 applicants. These statistics do not 
include our subsidiaries.
Infosys Integrated Annual Report 2025-26
116
Education, training and assessment (ETA)
Infosys continues to invest in developing human potential for the 
orga
```

</details>
<details><summary>[3] infosys_2025_26_annual_report.pdf p.84 — score 0.557</summary>

```
tices to ensure that we do not condone human 
rights violations or abuses. 
Further details are available in the Infosys Code of Conduct: 
https://www.infosys.com/investors/corporate-Governance/
documents/codeofconduct.pdf.
Recruitment
As of March 31, 2026, the Group employed 3,28,594 employees, 
of which 3,10,887 were professionals involved in service delivery 
to clients, including trainees.
We continually seek and employ a diverse workforce across 
various IT fields. We have established stron
```

</details>
<details><summary>[4] infosys_2025_26_annual_report.pdf p.25 — score 0.547</summary>

```
he Infosys 
Knowledge Institute (IKI)
600+ IT & industry agents built on Infosys  
Topaz Fabric
973 Patents in the portfolio (granted / pending)
 • Diversified portfolio of solutions 
across industry segments
 • Innovation partner to clients
 • Partner of choice for social and 
environmental solutions for the 
community
Human Capital
20,000+ Fresh graduates hired globally 
39.5% Women in the workforce
155 Nationalities in the workforce
 • Infosys has been recognized as a 
Global Top Employer for
```

</details>
<details><summary>[5] infosys_2025_26_annual_report.pdf p.324, 325 — score 0.543</summary>

```
ment term ending 
on March 31, 2027 have not been granted as of March 31, 2026, 
since the service commencement date precedes the grant date, 
the company has recorded employment stock compensation 
expense in accordance with Ind AS 102, Share based payment. The 
grant date for this purpose in accordance with Ind AS 102, Share 
based payment, is July 1, 2022.
Infosys Integrated Annual Report 2025-26
356
Under the 2019 Plan
The Board, on April 17, 2025, based on the recommendations 
of the Nomina
```

</details>

---

## q023

**Question:** What share of Infosys staff is AI-aware, and how many hours did employees spend learning on average in fiscal 2026?

**Reference answer:** 84% of the workforce is AI-aware, and average annual learning hours were 113.

**Model answer:** 84% of Infosys staff is AI-aware. I don't know.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] infosys_2025_26_annual_report.pdf p.26, 27 — score 0.645</summary>

```
ing shareholder value.
`23,865
2024
`34,549
2025
`33,097
2026
Free cash flows in ` crore and as a % of
net profit 
90.9% 129.2% 112.3%
Infosys Integrated Annual Report 2025-26 Infosys Integrated Annual Report 2025-26
53
Human Capital
Delivering value
Performance highlights
3,28,594
Employees globally
155
Nationalities in the workforce
84%
AI-aware employees
79%
Employee satisfaction score
39.5%
Women in the workforce
52
Material topics
• Employee Value Proposition
• Employee health and wellness

```

</details>
<details><summary>[2] infosys_2025_26_annual_report.pdf p.18 — score 0.627</summary>

```
nlock value from AI at speed and scale. Infosys is 
emerging as a leader in AI services, with AI-led programs now 
deployed across 90% of our top 200 clients and rapidly scaling 
across industries.
Infosys is well-positioned as the leading company for AI services.
Our AI strategy is built on six core pillars of our AI-First value 
framework – strategy & engineering, data, process, legacy 
modernization, physical AI, and trust – together addressing a 
US$300 billion opportunity, based on market e
```

</details>
<details><summary>[3] infosys_2025_26_annual_report.pdf p.88 — score 0.623</summary>

```
ip capability through its AI 
for Business Growth program, delivered in partnership with 
Kellogg. Over the last two years, more than 1,500 senior leaders 
across Infosys have completed this program, complemented 
by focused sessions with internal leaders and external subject 
matter experts. A day-long AI immersion program designed 
for senior leaders to build hands-on experience with AI tools, 
including Infosys Topaz Fabric to solve real industry problems 
further strengthened AI fluency acro
```

</details>
<details><summary>[4] infosys_2025_26_annual_report.pdf p.16, 17 — score 0.618</summary>

```
ed as one of the 2026 World’s Most Ethical 
Companies by Ethisphere for the sixth consecutive year.
84%
of the workforce enabled on AI
Infosys Integrated Annual Report 2025-26 31Infosys Integrated Annual Report 2025-2630
14.9

Infosys Integrated Annual Report 2025-26
33
Infosys Integrated Annual Report 2025-2632
 Infosys Integrated Annual Report 2025-2632
 Infosys Integrated Annual Report 2025-26 33
Nandan M. Nilekani
Chairman
Chairman’s message
Performance overview
Whenever there is a major tec
```

</details>
<details><summary>[5] infosys_2025_26_annual_report.pdf p.27, 28 — score 0.618</summary>

```
to performance management and 
continuous learning till offboarding. 
Our approach to AI adoption within 
the HR function is grounded in a 
simple belief: technology should 
make work more human.

Infosys Integrated Annual Report 2025-26 Infosys Integrated Annual Report 2025-26
54 55
Intellectual Capital
Delivering value
Material topics
• Innovation and Intellectual 
Property
• Products, platforms and solutions
• Responsible AI
UN SDG mapping
Our Intellectual Capital is driven by agility, flexib
```

</details>

---

## q024

**Question:** How many Infosys clients were in the $100 million-plus bracket in fiscal 2026, against the prior year?

**Reference answer:** 41 in fiscal 2026, up from 39 in fiscal 2025, on a consolidated basis.

**Model answer:** In fiscal 2026, there were 41 Infosys clients in the $100 million-plus bracket, compared to 39 clients in the prior year (fiscal 2025).

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] infosys_2025_26_annual_report.pdf p.88 — score 0.718</summary>

```
porations. Our total client base at the end of the year stood 
at 1,965. The client segmentation, based on the last 12 months’ 
revenue for the current and previous years, on a consolidated 
basis, is as follows:
Clients 2026 2025
100 million dollar + 41 39
50 million dollar + 88 85
10 million dollar + 328 309
1 million dollar + 1,018 992
5. Infosys Leadership Institute (ILI)
As artificial intelligence continues to redefine enterprise 
priorities, the Infosys Leadership Institute (ILI) plays a p
```

</details>
<details><summary>[2] infosys_2025_26_annual_report.pdf p.271, 272 — score 0.631</summary>

```
mited  956  1,001 
Infosys Public Services  682  659 
Infosys Compaz Pte Ltd  171  160 
Infosys Consulting Ltda  1 –
Simplus Australia Pty Ltd  1  2 
Infosys Chile SpA  5  7 
Blue Acorn iCi Inc –  2 
Portland Group Pty Ltd  3 –
Kaleidoscope Animations, Inc. –  1 
Infosys Singapore Pte. Ltd.  1 –
Infosys Integrated Annual Report 2025-26
303
Particulars
Year ended March 31, 
2026 2025
BASE life science A/S  15  14 
BASE life science GmbH –  1 
Infosys Business Solutions LLC  13 –
Infosys South Afr
```

</details>
<details><summary>[3] infosys_2025_26_annual_report.pdf p.77, 78 — score 0.625</summary>

```
ncy grew by 3.1%.
We added 443 new customers (gross) during fiscal 2026 as 
compared to 365 new customers (gross) during fiscal 2025.
Management’s discussion and analysis
Infosys Integrated Annual Report 2025-26
109
On a consolidated basis, for the year ended March 31, 2026, 
approximately 97.1% were export revenues whereas 2.9% were 
domestic revenues, while for the year ended March 31, 2025, 
2. Expenditure
The following table gives an overview of the standalone and consolidated operating expe
```

</details>
<details><summary>[4] infosys_2025_26_annual_report.pdf p.88, 89 — score 0.621</summary>

```
d with 
over 1,000 clients and created over 2,000 assets since inception. 
For more information, visit https://infosys.com/iki.
Infosys Integrated Annual Report 2025-26
120
7. ESG vision and ambitions
In October 2020, we launched our ESG Vision 2030 to ‘shape and 
share solutions that serve the development of businesses and 
communities.’ Our vision continues to reflect our commitment 
to responsible business. In fiscal 2025, at the mid-point of 
our journey towards our 2030 goals, we had an opp
```

</details>
<details><summary>[5] infosys_2025_26_annual_report.pdf p.271 — score 0.615</summary>

```
a  8 –
WongDoody, Inc –  6 
Infosys McCamish Systems LLC  34  1 
Infosys Green Forum  44  42 
Kaleidoscope Animations, Inc. –  1 
Infosys Mexico –  1 
Outbox systems Inc. dba Simplus (US) –  2 
Infosys Consulting AG  4  2 
Infosys Automotive and Mobility GmbH 
& Co.KG  163  150 
Wongdoody GmbH  10  9 
Particulars
Year ended March 31, 
2026 2025
Infosys Nova Holdings LLC  4  2 
Infosys Technologies (Sweden) AB. –  1 
Infosys Singapore Pte. Ltd.  3  9 
Infosys Compaz Pte. Ltd  2 –
GuideVision, s.r
```

</details>

---

## q025

**Question:** What did the Labour Codes notified in November 2025 do to the Infosys numbers, and how did the effect differ between standalone and consolidated reporting?

**Reference answer:** They raised gratuity liability and compensated absences by ₹1,146 crore standalone and ₹1,289 crore consolidated, which cut operating margin by 0.8% standalone and 0.7% consolidated.

**Model answer:** The Labour Codes notified in November 2025 had a non-recurring impact on Infosys, resulting in an increase in the past service cost and increased compensated absences by ₹1,289 crore. This incremental amount was presented as "Impact of Labour Codes" under "Exceptional Item" in the Consolidated Statement of Profit and Loss for the year ended March 31, 2026. The effect on diluted EPS, excluding the impact of these Labour Codes, was an increase of 16.0% on a standalone basis and 12.2% on a consolidated basis for the year ended March 31, 2026.

**Retrieved context (5 chunks, the ONLY thing the model saw):**

<details><summary>[1] alivus_2025_26_annual_report.pdf p.118 — score 0.681</summary>

```
ave been consolidated into a unified framework 
comprising four Labour Codes (collectively referred to as the “New Labour Codes”), which became effective from 21 November 2025. The Company has reassessed 
its employee benefit obligations in accordance with the revised definition of wages under the New Labour Codes.
Considering the material, regulatory-driven, and non-recurring nature of the impact, the Company has presented the incremental effect as “Statutory impact of 
New Labour Codes” under 
```

</details>
<details><summary>[2] ganesh_2025_26_annual_report.pdf p.287 — score 0.649</summary>

```
rising 4 Labour 
Codes viz; the Code on Wages, 2019, the Code on Social Security, 2020, the Industrial Relations Code, 2020 and the 
Occupational Safety, Health and working Conditions Code, 2020 (Collectively referred to as the “Codes”) which were 
made effective from November 21,2025. The corresponding supporting rules under these codes are yet to be notified. 
The Group has considered the impact on the basis of best information available consistent with the guidance provided 
by the Institute 
```

</details>
<details><summary>[3] infosys_2025_26_annual_report.pdf p.336 — score 0.635</summary>

```
ising out of past service cost and 
increase in compensated absences by `1,289 crore. Considering 
the impact arising out of an enactment of the new legislation 
is an event of non-recurring nature, the Group has presented 
this incremental amount as “Impact of Labour Codes” under 
“Exceptional Item” in the Consolidated Statement of Profit and 
Loss for the year ended March 31, 2026. The Group continues 
to monitor the developments pertaining to Labour Codes 
and will evaluate impact if any on t
```

</details>
<details><summary>[4] infosys_2025_26_annual_report.pdf p.33, 34 — score 0.629</summary>

```
e and consolidated basis for the year ended March 31, 2026.
(3) Excluding the effect of Income Tax orders received under Sections 250 and 254 of the Income-tax Act, 1961 and The Labour Codes provisions notified by the 
Government of India, Diluted EPS increase (in ` terms) is 16.0% and 12.2% YoY on standalone and consolidated basis for the year ended March 31, 2026.
Board's report
Statutory reports
Infosys Integrated Annual Report 2025-26
65
Financial position
(In ` crore)
Particulars Standalone
```

</details>
<details><summary>[5] rishiroop_2025_26_annual_report.pdf p.103 — score 0.613</summary>

```
54.90  122.09  44.48  85.74
Net liability  60.17  138.78  48.38  100.07
27.1 On November 21, 2025, the Government of India notified provisions of the Code on Wages, 2019, the 
Industrial Relations Code, 2020, the Code on Social Security, 2020, and the Occupational Safety, Health 
and Working Conditions Code, 2020 (Labour Codes), which consolidate twenty-nine existing labour laws 
into a unified framework governing employee benefits during employment and post-employment. 
The Labour Codes, amongs
```

</details>
