import pandas

'''
http://sebastianraschka.com/Articles/2014_pca_step_by_step.html
http://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html
http://scikit-learn.org/stable/tutorial/basic/tutorial.html
'''

In [87]: df
Out[87]:
                                   Algeria  Angola  Argentina  Armenia  \
2016_gdp_growth                        1.4     1.3       -1.1      2.7
2016_cpi                               6.7    25.5       41.4     -0.4
2016_ca_balance_per_gdp              -15.1    -8.9       -2.7     -0.8
2016_reserves_months_import_cover     25.4     8.9        5.1      4.4
2016_fdi_per_gdp                      -0.3     1.1        1.6      1.6
2016_gross_debt_per_gdp                3.8    39.4       29.2     80.9
2016_budget_balance                  -15.2    -7.0       -4.9     -5.1
2016_credit_growth                    70.0     4.5       35.3     11.3

                                   Azerbaijan  Bangladesh  Belarus  Brazil  \
2016_gdp_growth                          -3.1         6.5     -2.1    -3.0
2016_cpi                                 11.3         5.6     14.0     8.2
2016_ca_balance_per_gdp                  -1.8         1.4     -3.8    -1.3
2016_reserves_months_import_cover         5.9         7.5      1.7    19.8
2016_fdi_per_gdp                         13.1         0.8      3.9     3.0
2016_gross_debt_per_gdp                  37.6        16.6     71.2    31.7
2016_budget_balance                      -3.5        -5.2      0.6    -8.1
2016_credit_growth                      -12.0        14.3      7.0     8.4

                                   Chile  China   ...    Philippines  Russia  \
2016_gdp_growth                      1.6    6.6   ...            5.8    -0.8
2016_cpi                             4.1    2.3   ...            1.8     7.2
2016_ca_balance_per_gdp             -2.1    3.1   ...            3.1     2.9
2016_reserves_months_import_cover    6.3   17.8   ...           11.1    18.1
2016_fdi_per_gdp                     0.6   -0.3   ...            0.2    -1.5
2016_gross_debt_per_gdp             65.2    8.9   ...           25.6    42.3
2016_budget_balance                 -2.5   -3.5   ...           -0.8    -3.9
2016_credit_growth                  11.0   19.6   ...           13.3    13.0

                                   SOAF  SRILAN  Tajikistan  Turkey  Uganda  \
2016_gdp_growth                     0.8     5.1        -1.0     3.5     4.3
2016_cpi                            6.5     4.3         8.0     7.5     5.6
2016_ca_balance_per_gdp            -4.3    -2.3        -6.2    -4.3    -7.8
2016_reserves_months_import_cover   5.3     3.6         1.8     6.1     4.5
2016_fdi_per_gdp                   -0.7     2.0         3.2     1.3     3.6
2016_gross_debt_per_gdp            44.9    57.5        69.9    55.3    24.4
2016_budget_balance                -3.3    -5.4        -2.5    -1.7    -6.6
2016_credit_growth                  2.2    18.5        14.3    11.1    10.6

                                   Ukraine  Vietnam  Zambia
2016_gdp_growth                        0.6      6.3     3.0
2016_cpi                              13.0      1.5    20.7
2016_ca_balance_per_gdp               -1.1      0.7    -3.3
2016_reserves_months_import_cover      4.2      2.4     3.1
2016_fdi_per_gdp                       5.0      4.8     3.7
2016_gross_debt_per_gdp              152.5     37.6    43.8
2016_budget_balance                   -3.7     -3.7    -7.8
2016_credit_growth                     6.2     18.6     1.9

[8 rows x 39 columns]

from sklearn.decomposition import PCA as sklearnPCA
sklearn_pca = sklearnPCA(n_components=2)


X = df.T

X_s = StandardScaler().fit_transform(X)

data = sklearn_pca.fit_transform(X_s)

xdata=data[:,0]

ydata=data[:,1]

labels = df.columns

fig = plt.figure()

ax = fig.add_axes((0.1,0.15,0.8,0.7))

ax.scatter(xdata,ydata,marker='.')

for label,x,y in zip(labels,xdata,ydata):
	ax.annotate(label,xy = (x, y), xytext = (0, -10),textcoords = 'offst points', ha = 'center', va = 'center', size=8)

plt.show()