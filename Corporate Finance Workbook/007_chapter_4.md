---
author:
- CFA Institute
- Martin S. Fridson
- George H. Troughton
chapter: CHAPTER 4
chapter_index: 7
converted_at: '2026-08-31T08:33:30.291620+00:00'
converted_date: '2026-08-31'
description: 'Evaluate your understanding of corporate finance with practice for today''s
  professional Corporate Finance: Economic Foundations and Financial Modeling Workbook,
  3rd Edition offers the key component of effective learning—practice. Designed for
  both students and investment professionals, this companion workbook aligns with
  the latest Corporate Finance text chapter-by-chapter. To improve your comprehension
  of core concepts, this book includes brief chapter summaries before diving into
  challenging practice questions and their solutions, while also laying out learning
  objectives so you can understand the "why" of each exercise. Corporate Finance:
  Economic Foundations and Financial Modeling Workbook, 3rd Edition will help you:
  Synthesize essential material from the main Corporate Finance text using real-world
  applications. Understand the key fundamentals of the corporate finance discipline.
  Work toward...'
file_hash_sha256: 73363d7cd1631f19af1c188ced739bde121faab271dd15c1b198ecd79309c2fd
file_size_kb: 1206.52
file_type: .epub
identifier: urn:isbn:9781119743798
language: en-US
published_date: '2022-09-22T00:00:00Z'
publisher: Wiley
source_file: tmpe6wm42j4.epub
title: Corporate Finance Workbook
total_chapters: 36
word_count: 2295
---

xml version='1.0' encoding='utf-8'?

CHAPTER 4
=========

CAPITAL INVESTMENTS
===================

LEARNING OUTCOMES
-----------------

*The candidate should be able to:*

* describe types of capital investments made by companies
* describe the capital allocation process and basic principles of capital allocation
* demonstrate the use of net present value (NPV) and internal rate of return (IRR) in allocating capital and describe the advantages and disadvantages of each method
* describe common capital allocation pitfalls
* describe expected relations among a company’s investments, company value, and share price
* describe types of real options relevant to capital investment

SUMMARY
-------

Capital investments—those investments with a life of one year or longer—are key in determining whether a company is profitable and generating value for its shareholders. Capital allocation is the process companies use to decide their capital investment activity. This chapter introduces capital investments, basic principles underlying the capital allocation model, and the use of NPV and IRR decision criteria.

* Companies invest for two reasons: to maintain their existing businesses and to grow them. Projects undertaken by companies to maintain a business including operating efficiencies are (1) going concern projects and (2) regulatory/compliance projects, while (3) expansion projects and (4) other projects are undertaken by companies to strategically expand or grow their operations.
* Capital allocation supports the most critical investments for many corporations—their investments in long-term assets. The principles of capital allocation are also relevant and can be applied to other corporate investing and financing decisions and to security analysis and portfolio management.
* The typical steps companies take in the capital allocation process are (1) idea generation, (2) investment analysis, (3) capital allocation planning, and (4) post-audit/monitoring.
* Companies should base their capital allocation decisions on the investment project’s incremental after-tax cash flows discounted at the opportunity cost of funds. In addition, companies should ignore financing costs because both the cost of debt and the cost of other capital are captured in the discount rate used in the analysis.
* The NPV of an investment project is the present value of its after-tax cash flows (or the present value of its after-tax cash inflows minus the present value of its after-tax outflows) or

  

  where the investment outlays are negative cash flows included in CF*t* and *r* is the required rate of return for the investment.
* Microsoft Excel functions to solve for the NPV for both conventional and unconventional cash flow patterns are

  + NPV or =NPV(rate, values) and
  + XNPV or =XNPV(rate, values, dates),

  where “rate” is the discount rate, “values” are the cash flows, and “dates” are the dates of each of the cash flows.
* The IRR is the discount rate that makes the present value of all future cash flows of the project sum to zero. This equation can be solved for the IRR:

  
* Using Microsoft Excel functions to solve for IRR, the functions are

  + IRR or =IRR(values, guess) and
  + XIRR or =XIRR(values, dates, guess),

  where “values” are the cash flows, “guess” is an optional user-specified guess that defaults to 10%, and “dates” are the dates of each cash flow.
* Companies should invest in a project if the NPV > 0 or if the IRR > *r.*
* For mutually exclusive investments that are ranked differently by the NPV and IRR, the NPV criterion is the more economically sound and the approach companies should use.
* The fact that projects with positive NPVs theoretically increase the value of the company and the value of its stock could explain the use and popularity of the NPV method by companies.
* Real options allow companies to make future decisions contingent on future economic information or events that change the value of capital investment decisions the company has made today. These can be classified as (1) timing options; (2) sizing options, which can be abandonment options or growth (expansion) options; (3) flexibility options, which can be price-setting options or production-flexibility options; and (4) fundamental options.

PRACTICE PROBLEMS
-----------------

1. With regard to capital allocation, an appropriate estimate of the incremental cash flows from an investment is *least likely* to include:

   1. externalities.
   2. interest costs.
   3. opportunity costs.
2. The NPV of an investment is equal to the sum of the expected cash flows discounted at the:

   1. internal rate of return.
   2. risk-free rate.
   3. opportunity COC.
3. A USD2.2 million investment will result in the following year-end cash flows:

   | Year |  | 1 |  | 2 |  | 3 |  | 4 |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | Cash flow (millions) |  | USD1.3 |  | USD1.6 |  | USD1.9 |  | USD0.8 |

   Using an 8% opportunity COC, the investment’s NPV is *closest* to:

   1. USD2.47 million.
   2. USD3.40 million.
   3. USD4.67 million.
4. The IRR is *best* described as the:

   1. opportunity COC.
   2. time-weighted rate of return.
   3. discount rate that makes the NPV equal to zero.
5. A three-year investment requires an initial outlay of GBP1,000. It is expected to provide three year-end cash flows of GBP200 plus a net salvage value of GBP700 at the end of three years. Its IRR is *closest* to:

   1. 10%.
   2. 11%.
   3. 20%.
6. Given the following cash flows for a capital investment, calculate the NPV and IRR. The required rate of return is 8%.

   | Year |  | 0 |  | 1 |  | 2 |  | 3 |  | 4 |  | 5 |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | Cash flow |  | –50,000 |  | 15,000 |  | 15,000 |  | 20,000 |  | 10,000 |  | 5,000 |

   |  |  | NPV |  |  |  | IRR |  |  |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | A |  | USD1,905 |  |  |  | 10.9% |  |  |
   | B |  | USD1,905 |  |  |  | 26.0% |  |  |
   | C |  | USD3,379 |  |  |  | 10.9% |  |  |
7. An investment of USD100 generates after-tax cash flows of USD40 in Year 1, USD80 in Year 2, and USD120 in Year 3. The required rate of return is 20%. The NPV is *closest* to:

   1. USD42.22.
   2. USD58.33.
   3. USD68.52.
8. An investment of USD150,000 is expected to generate an after-tax cash flow of USD100,000 in one year and another USD120,000 in two years. The COC is 10%. What is the IRR?

   1. 28.39%
   2. 28.59%
   3. 28.79%
9. Kim Corporation is considering an investment of KRW750 million with expected after-tax cash inflows of KRW175 million per year for seven years. The required rate of return is 10%. What is the investment’s:

   |  |  | NPV? |  |  |  | IRR? |  |  |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | A. |  | KRW102 million |  |  |  | 14.0% |  |  |
   | B. |  | KRW157 million |  |  |  | 23.3% |  |  |
   | C. |  | KRW193 million |  |  |  | 10.0% |  |  |
10. Erin Chou is reviewing a profitable investment that has a conventional cash flow pattern. If the cash flows for the initial outlay and future after-tax cash flows all double, Chou would predict that the IRR would:

    1. increase and the NPV would increase.
    2. stay the same and the NPV would increase.
    3. stay the same and the NPV would stay the same.
11. Catherine Ndereba is an energy analyst tasked with evaluating a crude oil exploration and production company. The company previously announced that it plans to embark on a new project to drill for oil offshore. As a result of this announcement, the stock price increased by 10%. After conducting her analysis, Ms. Ndereba concludes that the project does indeed have a positive NPV. Which statement is true?

    1. The stock price should remain where it is because Ms. Ndereba’s analysis confirms that the recent run-up was justified.
    2. The stock price should go even higher now that an independent source has confirmed that the NPV is positive.
    3. The stock price could remain steady, move higher, or move lower.
12. The Bearing Corp. invests only in positive-NPV projects. Which of the following statements is true?

    1. Bearing’s ROIC is greater than its COC.
    2. Bearing’s COC is greater than its ROIC.
    3. We cannot reach any conclusions about the relationship between the company’s ROIC and COC.
13. Investments 1 and 2 have similar outlays, although the patterns of future cash flows are different. The cash flows, as well as the NPV and IRR, for the two investments are shown below. For both investments, the required rate of return is 10%.

    |  |  | Cash Flows | | | | | | | | |  |  |  |  |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | Year |  | 0 |  | 1 |  | 2 |  | 3 |  | 4 |  | NPV |  | IRR (%) |
    | Investment 1 |  | –50 |  | 20 |  | 20 |  | 20 |  | 20 |  | 13.40 |  | 21.86 |
    | Investment 2 |  | –50 |  | 0 |  | 0 |  | 0 |  | 100 |  | 18.30 |  | 18.92 |

    The two projects are mutually exclusive. What is the appropriate investment decision?

    1. Invest in both investments.
    2. Invest in Investment 1 because it has the higher IRR.
    3. Invest in Investment 2 because it has the higher NPV.
14. Consider the two investments below. The cash flows, as well as the NPV and IRR, for the two investments are given. For both investments, the required rate of return is 10%.

    |  |  | Cash Flows | | | | | | | | |  |  |  |  |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | Year |  | 0 |  | 1 |  | 2 |  | 3 |  | 4 |  | NPV |  | IRR (%) |
    | Investment 1 |  | –100 |  | 36 |  | 36 |  | 36 |  | 36 |  | 14.12 |  | 16.37 |
    | Investment 2 |  | –100 |  | 0 |  | 0 |  | 0 |  | 175 |  | 19.53 |  | 15.02 |

    What discount rate would result in the same NPV for both investments?

    1. A rate between 0.00% and 10.00%
    2. A rate between 10.00% and 15.02%
    3. A rate between 15.02% and 16.37%
15. Wilson Flannery is concerned that the following investment has multiple IRRs.

    | Year |  | 0 |  | 1 |  | 2 |  | 3w |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | Cash flows |  | –50 |  | 100 |  | 0 |  | –50 |

    How many discount rates produce a zero NPV for this investment?

    1. One, a discount rate of 0%
    2. Two, discount rates of 0% and 32%
    3. Two, discount rates of 0% and 62%
16. What type of project is *most likely* to yield new revenues for a company?

    1. Regulatory/compliance
    2. Going concern
    3. Expansion

**The following information relates to questions 17–19**

Bouchard Industries is a Canadian company that manufactures gutters for residential houses. Its management believes it has developed a new process that produces a superior product. The company must make an initial investment of CAD190 million to begin production. If demand is high, cash flows are expected to be CAD40 million per year. If demand is low, cash flows will be only CAD20 million per year. Management believes there is an equal chance that demand will be high or low. The investment, which has an investment horizon of ten years, also gives the company a production-flexibility option allowing the company to add shifts at the end of the first year if demand turns out to be high. If the company exercises this option, net cash flows would increase by an additional CAD5 million in Years 2–10. Bouchard’s opportunity cost of funds is 10%.

The internal auditor for Bouchard Industries has made two suggestions for improving capital allocation processes at the company. The internal auditor’s suggestions are as follows:

Suggestion 1: “In order to treat all capital allocation proposals in a fair manner, the investments should all use the risk-free rate for the required rate of return.”

Suggestion 2: “When rationing capital, it is better to choose the portfolio of investments that maximizes the company NPV than the portfolio that maximizes the company IRR.”

17. What is the NPV (CAD millions) of the original project for Bouchard Industries without considering the production-flexibility option?

    1. –CAD6.11 million
    2. –CAD5.66 million
    3. CAD2.33 million
18. What is the NPV (CAD millions) of the optimal set of investment decisions for Bouchard Industries including the production-flexibility option?

    1. –CAD6.34 million
    2. CAD7.43 million
    3. CAD31.03 million
19. Should the capital allocation committee accept the internal auditor’s suggestions?

    1. No for Suggestions 1 and 2
    2. No for Suggestion 1 and yes for Suggestion 2
    3. Yes for Suggestion 1 and no for Suggestion 2