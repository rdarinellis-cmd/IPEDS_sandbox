import pandas as pd
df = pd.read_csv('msu_om.csv')
ftft = df[(df['ftpt'] == 1) & (df['class_level'] == 1) & (df['fed_aid_type'] == 99)].sort_values('year')
print(ftft[['year', 'cohort_adj', 'completion_rate_4yr', 'completion_rate_6yr', 'completion_rate_8yr', 'transfer_rate_8yr', 'still_enroll_rate_8yr']])
