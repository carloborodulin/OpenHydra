# Revisions in release 20261123T064001Z

Compared with release 2026-06-11-reconstructed.

### summarized.parquet

Rows 259200 -> 259200. Keys added 0, removed 0, values changed 41103.

| level | area | offense | series | measure | period | old | new | change |
|---|---|---|---|---|---|---|---|---|
| national | US | property-crime | clearances | actual | 2024-06-01 | 74,657.00 | 75,676.00 | +1,019.00 (+1.4%) |
| national | US | property-crime | clearances | actual | 2024-09-01 | 74,876.00 | 75,794.00 | +918.00 (+1.2%) |
| national | US | property-crime | offenses | actual | 2024-12-01 | 522,346.00 | 523,197.00 | +851.00 (+0.2%) |
| state | NY | property-crime | clearances | actual | 2024-06-01 | 6,564.00 | 7,413.00 | +849.00 (+12.9%) |
| national | US | property-crime | offenses | actual | 2024-06-01 | 485,836.00 | 486,659.00 | +823.00 (+0.2%) |
| national | US | larceny | clearances | actual | 2024-06-01 | 57,661.00 | 58,444.00 | +783.00 (+1.4%) |
| state | NY | property-crime | clearances | actual | 2024-09-01 | 5,927.00 | 6,671.00 | +744.00 (+12.6%) |
| national | US | larceny | clearances | actual | 2024-09-01 | 58,137.00 | 58,863.00 | +726.00 (+1.2%) |
| national | US | property-crime | offenses | actual | 2024-10-01 | 496,810.00 | 497,533.00 | +723.00 (+0.1%) |
| national | US | property-crime | offenses | actual | 2024-11-01 | 458,278.00 | 458,997.00 | +719.00 (+0.2%) |

### agencies.parquet

Rows 19619 -> 19725. Keys added 172, removed 66, values changed 161.

### arrests.parquet

Rows 86625 -> 462000. Keys added 375375, removed 0, values changed 11309.

| level | area | offense | arrest_code | window_from | window_to | category | label | old | new | change |
|---|---|---|---|---|---|---|---|---|---|---|
| national | US | all | all | 01-2015 | 12-2024 | Arrestee Sex | Male | 56,563,131.00 | 56,594,654.00 | +31,523.00 (+0.1%) |
| national | US | all | all | 01-2015 | 12-2024 | Arrestee Race | White | 50,955,787.00 | 50,983,275.00 | +27,488.00 (+0.1%) |
| national | US | all | all | 01-2015 | 12-2024 | Offense Breakdown | All Other Offenses (Except Traffic) | 25,116,658.00 | 25,131,429.00 | +14,771.00 (+0.1%) |
| national | US | all | all | 01-2015 | 12-2024 | Offense Category | All Other Offenses | 25,116,658.00 | 25,131,429.00 | +14,771.00 (+0.1%) |
| national | US | all | all | 01-2015 | 12-2024 | Offense Name | All Other Offenses | 25,116,658.00 | 25,131,429.00 | +14,771.00 (+0.1%) |
| national | US | all | all | 01-2015 | 12-2024 | Arrestee Race | Black or African American | 20,808,949.00 | 20,821,434.00 | +12,485.00 (+0.1%) |
| national | US | all | all | 01-2015 | 12-2024 | Arrestee Sex | Female | 20,990,469.00 | 21,000,686.00 | +10,217.00 (+0.0%) |
| state | NY | all | all | 01-2015 | 12-2024 | Arrestee Sex | Male | 1,776,566.00 | 1,783,935.00 | +7,369.00 (+0.4%) |
| state | FL | all | all | 01-2015 | 12-2024 | Arrestee Sex | Male | 1,790,363.00 | 1,796,181.00 | +5,818.00 (+0.3%) |
| state | FL | all | all | 01-2015 | 12-2024 | Arrestee Race | White | 492,341.00 | 497,612.00 | +5,271.00 (+1.1%) |

### pe.parquet

Rows 2750 -> 2750. Keys added 0, removed 0, values changed 14.

| level | area | section | metric | year | old | new | change |
|---|---|---|---|---|---|---|---|
| national | US | actual | Male Officers | 2023 | 651,516.00 | 651,534.00 | +18.00 (+0.0%) |
| state | AL | actual | Male Officers | 2024 | 11,110.00 | 11,128.00 | +18.00 (+0.2%) |
| state | AL | actual | Male Officers | 2023 | 10,882.00 | 10,900.00 | +18.00 (+0.2%) |
| national | US | actual | Male Officers | 2024 | 661,843.00 | 661,861.00 | +18.00 (+0.0%) |
| state | AL | actual | Female Civilians | 2024 | 3,734.00 | 3,748.00 | +14.00 (+0.4%) |
| national | US | actual | Female Civilians | 2024 | 215,641.00 | 215,655.00 | +14.00 (+0.0%) |
| national | US | actual | Female Civilians | 2023 | 209,098.00 | 209,111.00 | +13.00 (+0.0%) |
| state | AL | actual | Female Civilians | 2023 | 3,673.00 | 3,686.00 | +13.00 (+0.4%) |
| state | AL | actual | Male Civilians | 2024 | 2,072.00 | 2,076.00 | +4.00 (+0.2%) |
| national | US | actual | Male Civilians | 2024 | 147,330.00 | 147,334.00 | +4.00 (+0.0%) |

### hate_crime.parquet

Rows 15125 -> 15675. Keys added 1100, removed 550, values changed 1986.

| level | area | category | label | old | new | change |
|---|---|---|---|---|---|---|
| national | US | bias_category | Race/Ethnicity/Ancestry | 53,620.00 | 51,174.00 | -2,446.00 (-4.6%) |
| national | US | offense_type | Intimidation | 35,442.00 | 33,901.00 | -1,541.00 (-4.3%) |
| national | US | bias | Anti-Black or African American | 27,343.00 | 26,183.00 | -1,160.00 (-4.2%) |
| national | US | bias_category | Religion | 19,222.00 | 18,094.00 | -1,128.00 (-5.9%) |
| national | US | offender_race | White | 42,519.00 | 41,441.00 | -1,078.00 (-2.5%) |
| national | US | offense_type | Destruction/Damage/Vandalism of Property | 26,459.00 | 25,429.00 | -1,030.00 (-3.9%) |
| national | US | bias_category | Sexual Orientation | 15,965.00 | 14,938.00 | -1,027.00 (-6.4%) |
| state | NJ | bias_category | Race/Ethnicity/Ancestry | 5,337.00 | 4,417.00 | -920.00 (-17.2%) |
| national | US | offender_ethnicity | Unknown | 20,726.00 | 19,872.00 | -854.00 (-4.1%) |
| national | US | bias | Anti-Jewish | 11,696.00 | 10,951.00 | -745.00 (-6.4%) |

### shr.parquet

Rows 7260 -> 7260. Keys added 55, removed 55, values changed 1431.

| level | area | category | label | old | new | change |
|---|---|---|---|---|---|---|
| national | US | offender_sex | Male | 131,328.00 | 131,657.00 | +329.00 (+0.3%) |
| national | US | offender_ethnicity | Not Hispanic or Latino | 76,388.00 | 76,640.00 | +252.00 (+0.3%) |
| national | US | offender_race | Black or African American | 82,195.00 | 82,422.00 | +227.00 (+0.3%) |
| national | US | offender_age | 20-29 | 54,091.00 | 54,239.00 | +148.00 (+0.3%) |
| national | US | offender_race | White | 59,798.00 | 59,920.00 | +122.00 (+0.2%) |
| national | US | offender_ethnicity | Not Specified | 53,190.00 | 53,089.00 | -101.00 (-0.2%) |
| national | US | offender_age | 30-39 | 31,782.00 | 31,875.00 | +93.00 (+0.3%) |
| national | US | victim_ethnicity | Not Hispanic or Latino | 97,114.00 | 97,198.00 | +84.00 (+0.1%) |
| national | US | victim_sex | Male | 129,200.00 | 129,284.00 | +84.00 (+0.1%) |
| national | US | offender_sex | Not Specified | 14,334.00 | 14,252.00 | -82.00 (-0.6%) |

### property.parquet

Rows 7890 -> 75700. Keys added 75700, removed 7890, values changed 0.

### nibrs.parquet

Rows 154548 -> 165360. Keys added 11448, removed 636, values changed 29821.

| level | area | offense | category | label | old | new | change |
|---|---|---|---|---|---|---|---|
| national | US | 13B | offense_weapons | Personal Weapons | 11,466,170.00 | 11,472,380.00 | +6,210.00 (+0.1%) |
| national | US | 35A | offender_ethnicity | Not Hispanic or Latino | 4,657,505.00 | 4,663,713.00 | +6,208.00 (+0.1%) |
| national | US | 13B | victim_race | White | 9,184,272.00 | 9,190,372.00 | +6,100.00 (+0.1%) |
| national | US | 35A | victim_race | Not Specified | 8,102,949.00 | 8,108,635.00 | +5,686.00 (+0.1%) |
| national | US | 35A | victim_sex | Not Specified | 8,102,949.00 | 8,108,635.00 | +5,686.00 (+0.1%) |
| national | US | 35A | victim_ethnicity | Not Specified | 8,102,949.00 | 8,108,635.00 | +5,686.00 (+0.1%) |
| national | US | 13B | victim_location | Residence/Home | 8,844,744.00 | 8,849,910.00 | +5,166.00 (+0.1%) |
| national | US | 35A | offender_sex | Male | 7,176,452.00 | 7,181,541.00 | +5,089.00 (+0.1%) |
| national | US | 35A | offender_race | White | 6,506,485.00 | 6,511,528.00 | +5,043.00 (+0.1%) |
| national | US | 13B | victim_sex | Female | 8,455,732.00 | 8,460,549.00 | +4,817.00 (+0.1%) |

### lesdc.parquet

Rows 908 -> 908. Keys added 0, removed 0, values changed 0.

### nibrs_estimation.parquet

Rows 2949 -> 2949. Keys added 0, removed 0, values changed 0.

## Revisions in release 20261123T130946Z

Compared with release 20261123T064001Z.

### nibrs_estimation.parquet

Rows 2949 -> 2949. Keys added 0, removed 0, values changed 2925.

| level | area | offense | category | label | old | new | change |
|---|---|---|---|---|---|---|---|
| region | South | 102 | Offense_Location type | Schools, daycares, and universities | 29,512.00 | 29,512.00 | +0.00 (+0.0%) |
| national | US | 106 | Arrest_Arrestee race | Asian | 98.00 | 98.00 | +0.00 (+0.0%) |
| region | South | 105 | Arrest_Arrestee race | White | 15,888.00 | 15,888.00 | +0.00 (+0.0%) |
| national | US | 124 | Offense_Type of Weapon Involved | Personal weapons | 2,178,846.00 | 2,178,846.00 | +0.00 (+0.0%) |
| national | US | 106 | Offense_Location type | Residence/hotel | 9,961.00 | 9,961.00 | +0.00 (+0.0%) |
| region | South | 102 | Arrest_Arrestee armed with | Lethal cutting instrument | 1,927.00 | 1,927.00 | +0.00 (+0.0%) |
| region | Midwest | 55 | Victim_Victim race | Asian | 1,461.00 | 1,461.00 | +0.00 (+0.0%) |
| region | West | 133 | Arrest_Arrestee age | 5-14 | 2,980.00 | 2,980.00 | +0.00 (+0.0%) |
| region | West | 55 | Incident_Clearance Status | Exceptional clearance | 4,326.00 | 4,326.00 | +0.00 (+0.0%) |
| region | South | 124 | Arrest_Arrestee armed | Yes | 7,068.00 | 7,068.00 | +0.00 (+0.0%) |
