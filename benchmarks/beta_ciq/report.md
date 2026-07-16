# Benchmark des betas — réplication S&P Capital IQ

_Généré le 2026-07-06 par `benchmarks/beta_ciq/benchmark.py`._

Méthode CIQ (confirmée) : régression OLS brute, **5 ans, fréquence quotidienne**, fin de fenêtre = date d'export. Notre moteur (`comparables/finance/beta.py`) applique la même régression OLS (rendements simples, dates appariées). Configs candidates de notre outil : 5 ans et 2 ans en hebdomadaire, et le **défaut de l'outil** (période=5y, fréquence=1mo, indice local du registre).


## BETA 27032026.xlsx — Materiaux de construction (US)

Fin de fenêtre : **2026-03-27** — 2 sociétés résolues.

| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. | β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |
|---|---|---|---|---|---|---|---|---|---|
| Mueller Water Products, Inc. | 0.907 | 0.252 | 0.989 | ^GSPC | 0.301 | 0.989 | 1.090 | 1.133 | 1.152 |
| Omega Flex, Inc. | 0.772 | 0.109 | 0.854 | ^GSPC | 0.134 | 0.854 | 0.837 | 1.020 | 0.513 |
| **Médiane échantillon** | 0.839 | | 0.922 | | | 0.922 | 0.963 | 1.077 | 0.832 |

**Bande sectorielle Damodaran** (industrie retenue : *Machinery*, snapshot au 2026-01-05) :

| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |
|---|---|---|---|---|
| Global | 1.369 | 1.244 | 1.330 | 1553 |
| Europe | 1.117 | 1.029 | 1.084 | 210 |


## BETA FLO 27042026.xlsx — Agroalimentaire / fromages

Fin de fenêtre : **2026-04-27** — 7 sociétés résolues.

| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. | β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |
|---|---|---|---|---|---|---|---|---|---|
| Savencia SA | 0.265 | 0.034 | 0.273 | ^STOXX | 0.035 | 0.230 | 0.237 | 0.250 | 0.222 |
| Danone SA | 0.436 | 0.108 | 0.430 | ^STOXX | 0.108 | 0.401 | 0.349 | 0.172 | 0.399 |
| Schwaelbchen Molkerei Jakob Berz A | 0.085 | 0.000 | — | — | — | — | — | — | — |
| Glanbia Plc | 0.473 | 0.057 | 0.462 | ^STOXX | 0.055 | 0.390 | 0.365 | 0.375 | 0.515 |
| Emmi AG | 0.346 | 0.059 | 0.415 | ^STOXX | 0.092 | 0.558 | 0.542 | 0.427 | 0.542 |
| Fonterra Co-operative Group Limite | 0.156 | 0.006 | 0.097 | ^GSPC | 0.003 | 0.097 | 0.217 | 0.182 | 0.048 |
| Bega Cheese Limited | 1.043 | 0.186 | 0.893 | ^AXJO | 0.152 | 0.893 | 0.813 | 0.927 | 0.803 |
| **Médiane échantillon** | 0.346 | | 0.423 | | | 0.395 | 0.357 | 0.313 | 0.457 |

**Bande sectorielle Damodaran** (industrie retenue : *Food Processing*, snapshot au 2026-01-05) :

| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |
|---|---|---|---|---|
| Global | 0.674 | 0.528 | 0.560 | 1450 |
| Europe | 0.465 | 0.367 | 0.382 | 173 |


## BETA flo 25032026.xlsx — Materiaux de construction (mixte)

Fin de fenêtre : **2026-03-25** — 7 sociétés résolues.

| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. | β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |
|---|---|---|---|---|---|---|---|---|---|
| Geberit AG | 0.941 | 0.320 | 1.013 | ^STOXX | 0.374 | 1.042 | 1.189 | 0.887 | 1.324 |
| Westlake Corporation | 1.004 | 0.219 | 1.087 | ^GSPC | 0.249 | 1.087 | 1.023 | 0.955 | 0.769 |
| Advanced Drainage Systems, Inc. | 1.004 | 0.219 | 0.989 | ^STOXX | 0.109 | 1.337 | 1.479 | 1.253 | 1.375 |
| Georg Fischer AG | 1.229 | 0.384 | 1.296 | ^STOXX | 0.409 | 1.160 | 1.117 | 0.909 | 1.186 |
| Aalberts N.V. | 1.550 | 0.446 | 1.580 | ^STOXX | 0.464 | 1.292 | 1.410 | 1.297 | 1.401 |
| Genuit Group plc | 1.056 | 0.154 | 1.040 | ^FTSE | 0.156 | 1.040 | 1.421 | 1.746 | 2.105 |
| Wienerberger AG | 1.356 | 0.349 | 1.356 | ^STOXX | 0.352 | 1.128 | 1.136 | 1.443 | 1.269 |
| **Médiane échantillon** | 1.056 | | 1.087 | | | 1.128 | 1.189 | 1.253 | 1.324 |

**Bande sectorielle Damodaran** (industrie retenue : *Building Materials*, snapshot au 2026-01-05) :

| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |
|---|---|---|---|---|
| Global | 1.005 | 0.859 | 0.903 | 469 |
| Europe | 1.029 | 0.907 | 0.937 | 84 |


## Beta 01072026 Liste software.xlsx — Logiciels

Fin de fenêtre : **2026-07-01** — 10 sociétés résolues.

| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. | β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |
|---|---|---|---|---|---|---|---|---|---|
| SAP | 1.020 | 0.269 | 1.019 | ^STOXX | 0.269 | 0.986 | 0.971 | 1.000 | 1.139 |
| SalesForce | 1.168 | 0.277 | 1.253 | ^GSPC | 0.328 | 1.253 | 1.405 | 1.120 | 1.182 |
| ServiceNow | 1.388 | 0.289 | 1.474 | ^GSPC | 0.327 | 1.474 | 1.536 | 1.258 | 0.953 |
| PTC | 0.952 | 0.272 | 1.036 | ^GSPC | 0.327 | 1.036 | 0.971 | 0.902 | 1.000 |
| The Sage Group | 0.722 | 0.150 | 0.635 | ^STOXX | 0.125 | 0.555 | 0.673 | 0.632 | 0.245 |
| Nemetschek | 1.250 | 0.204 | 1.252 | ^STOXX | 0.207 | 1.091 | 1.108 | 1.082 | 0.737 |
| Pegasystems | 1.293 | 0.181 | 1.379 | ^GSPC | 0.206 | 1.379 | 1.440 | 1.238 | 0.877 |
| Temenos | 1.113 | 0.133 | 1.177 | ^STOXX | 0.150 | 1.034 | 0.856 | 0.364 | 1.204 |
| Kinaxis | 0.851 | 0.169 | 0.838 | ^GSPC | 0.167 | 0.910 | 0.848 | 0.559 | 0.756 |
| Axway (74Software) | 0.328 | 0.026 | 0.327 | ^STOXX | 0.026 | 0.257 | 0.435 | 0.646 | 0.356 |
| **Médiane échantillon** | 1.067 | | 1.107 | | | 1.035 | 0.971 | 0.951 | 0.915 |

**Bande sectorielle Damodaran** (industrie retenue : *Software (System & Application)*, snapshot au 2026-01-05) :

| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |
|---|---|---|---|---|
| Global | 1.354 | 1.297 | 1.331 | 1532 |
| Europe | 0.957 | 0.911 | 0.964 | 290 |


## Beta 29062026 FLO.xlsx — Paiements / fintech

Fin de fenêtre : **2026-06-29** — 11 sociétés résolues.

| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. | β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |
|---|---|---|---|---|---|---|---|---|---|
| Worldline SA | 1.557 | 0.093 | 1.567 | ^STOXX | 0.120 | 1.268 | 1.291 | 1.387 | 1.582 |
| Nexi S.p.A. | 1.315 | 0.267 | 1.333 | ^STOXX | 0.276 | 1.013 | 1.129 | 1.205 | 1.092 |
| CAB Payments Holdings | 0.553 | 0.014 | 0.512 | ^GSPC | 0.010 | 1.126 | 1.453 | 0.799 | 2.193 |
| Shift4 Payments, Inc. | 1.595 | 0.228 | 1.680 | ^GSPC | 0.251 | 1.680 | 1.608 | 1.510 | 1.380 |
| Block, Inc. | 2.183 | 0.392 | 2.270 | ^GSPC | 0.412 | 2.270 | 2.273 | 1.578 | 2.508 |
| Fiserv, Inc. | 0.742 | 0.119 | — | — | — | — | — | — | — |
| Global Payments Inc. | 1.121 | 0.270 | 1.206 | ^GSPC | 0.311 | 1.206 | 1.157 | 1.253 | 0.773 |
| Payal Holding Inc. | 1.336 | 0.294 | 1.422 | ^GSPC | 0.329 | 1.422 | 1.421 | 1.176 | 1.311 |
| NCR Voyix Corporation | 1.348 | 0.206 | 1.433 | ^GSPC | 0.263 | 1.433 | 1.460 | 1.581 | 1.373 |
| Hipay Group SA | 0.811 | 0.036 | 0.816 | ^STOXX | 0.037 | 0.710 | 0.990 | 0.813 | 1.587 |
| FleetCor Technologies, Inc. | 1.094 | 0.325 | 1.180 | ^GSPC | 0.380 | 1.180 | 1.169 | 1.336 | 0.887 |
| **Médiane échantillon** | 1.315 | | 1.378 | | | 1.237 | 1.356 | 1.294 | 1.376 |

Non couvertes : Network International (non couverte (sans ticker)).

**Bande sectorielle Damodaran** (industrie retenue : *Software (System & Application)*, snapshot au 2026-01-05) :

| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |
|---|---|---|---|---|
| Global | 1.354 | 1.297 | 1.331 | 1532 |
| Europe | 0.957 | 0.911 | 0.964 | 290 |


## Beta Flo 021225.xlsx — BTP / construction

Fin de fenêtre : **2025-12-02** — 10 sociétés résolues.

| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. | β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |
|---|---|---|---|---|---|---|---|---|---|
| Eiffage SA | 0.413 | 0.075 | 0.329 | ^GSPC | 0.062 | 0.896 | 0.932 | 1.018 | 0.803 |
| Bouygues SA | 0.327 | 0.058 | 0.237 | ^GSPC | 0.041 | 0.674 | 0.779 | 0.871 | 0.672 |
| HOCHTIEF Aktiengesellschaft | 0.558 | 0.083 | 0.497 | ^GSPC | 0.078 | 1.057 | 1.099 | 1.292 | 0.761 |
| Strabag SE | 0.369 | 0.034 | 0.292 | ^GSPC | 0.026 | 0.648 | 0.659 | 1.193 | 0.355 |
| Skanska AB (publ) | 0.602 | 0.100 | 0.461 | ^GSPC | 0.085 | 1.029 | 1.034 | 0.814 | 1.116 |
| Vinci SA | 0.407 | 0.080 | 0.327 | ^GSPC | 0.067 | 0.944 | 1.006 | 0.962 | 0.927 |
| Peab AB (publ) | 0.669 | 0.099 | 0.542 | ^GSPC | 0.088 | 1.060 | 1.094 | 0.975 | 1.335 |
| AF Gruppen ASA | 0.391 | 0.053 | 0.443 | ^STOXX | 0.065 | 0.452 | 0.559 | 0.565 | 0.686 |
| Keller Group plc | 0.521 | 0.064 | 0.408 | ^GSPC | 0.046 | 0.830 | 0.844 | 0.990 | 1.233 |
| NCC Group plc | 0.432 | 0.037 | 0.322 | ^GSPC | 0.023 | 0.827 | 0.649 | 0.864 | 1.147 |
| **Médiane échantillon** | 0.423 | | 0.368 | | | 0.863 | 0.888 | 0.968 | 0.865 |

**Bande sectorielle Damodaran** (industrie retenue : *Engineering/Construction*, snapshot au 2026-01-05) :

| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |
|---|---|---|---|---|
| Global | 1.001 | 0.637 | 0.759 | 1390 |
| Europe | 0.929 | 0.678 | 0.798 | 160 |


## Beta VFLO 0603.xlsx — Services informatiques

Fin de fenêtre : **2026-03-06** — 10 sociétés résolues.

| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. | β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |
|---|---|---|---|---|---|---|---|---|---|
| Computacenter plc | 0.947 | 0.165 | 0.934 | ^FTSE | 0.168 | 0.934 | 1.051 | 0.860 | 1.006 |
| Econocom Group SE | 0.693 | 0.083 | 0.693 | ^STOXX | 0.084 | 0.621 | 0.552 | 0.230 | 0.943 |
| CDW Corporation | 1.004 | 0.349 | 1.089 | ^GSPC | 0.418 | 1.089 | 1.077 | 1.203 | 1.043 |
| ePlus inc. | 0.978 | 0.214 | 1.064 | ^GSPC | 0.257 | 1.064 | 1.002 | 1.051 | 1.002 |
| Kyndryl Holdings, Inc. | 1.179 | 0.130 | 1.335 | ^GSPC | 0.156 | 1.335 | 1.482 | 1.678 | 1.981 |
| DXC Technology Company | 1.194 | 0.209 | 1.279 | ^GSPC | 0.235 | 1.279 | 1.250 | 0.954 | 1.029 |
| Atos SE | 1.496 | 0.026 | -1.499 | ^GSPC | 0.000 | -16.602 | -2.246 | -8.180 | -38.171 |
| Unisys Corporation | 1.432 | 0.131 | 1.518 | ^GSPC | 0.145 | 1.518 | 1.226 | 1.956 | 1.433 |
| Ricoh Company, Ltd. | 0.760 | 0.143 | 0.789 | ^N225 | 0.303 | 0.789 | 0.698 | 0.682 | 0.511 |
| Diebold Nixdorf, Incorporated | 0.450 | 0.068 | 0.798 | ^STOXX | 0.058 | 1.104 | 1.097 | 1.177 | 1.478 |
| **Médiane échantillon** | 0.991 | | 0.999 | | | 1.077 | 1.064 | 1.002 | 1.017 |

**Bande sectorielle Damodaran** (industrie retenue : *Computer Services*, snapshot au 2026-01-05) :

| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |
|---|---|---|---|---|
| Global | 1.117 | 1.004 | 1.072 | 1225 |
| Europe | 0.938 | 0.840 | 0.904 | 210 |


## Beta_ACIER_COSTE_240626.xlsx — Acier

Fin de fenêtre : **2026-06-24** — 8 sociétés résolues.

| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. | β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |
|---|---|---|---|---|---|---|---|---|---|
| Voestalpine AG | 1.411 | 0.361 | 1.412 | ^STOXX | 0.366 | 1.162 | 1.116 | 1.311 | 1.605 |
| Klöckner & Co SE | 1.184 | 0.169 | 1.189 | ^STOXX | 0.172 | 0.983 | 0.825 | 0.906 | 0.997 |
| Jacquet Metals | 1.022 | 0.194 | 1.028 | ^STOXX | 0.199 | 0.858 | 0.924 | 0.741 | 1.019 |
| Reliance Inc. | 0.750 | 0.205 | 0.834 | ^GSPC | 0.259 | 0.834 | 0.804 | 0.828 | 0.944 |
| Russel Metals | 0.782 | 0.236 | 0.776 | ^GSPC | 0.251 | 1.142 | 1.041 | 0.879 | 1.112 |
| Acerinox | 1.277 | 0.377 | 1.295 | ^STOXX | 0.393 | 1.009 | 0.891 | 1.011 | 1.261 |
| Outokumpu | 1.352 | 0.289 | 1.361 | ^STOXX | 0.304 | 1.245 | 1.164 | 1.426 | 1.665 |
| Salzgitter AG | 1.776 | 0.217 | 1.799 | ^STOXX | 0.225 | 1.523 | 1.523 | 1.693 | 2.007 |
| **Médiane échantillon** | 1.230 | | 1.242 | | | 1.075 | 0.983 | 0.958 | 1.187 |

Non couvertes : Olympic Steel (non couverte (sans ticker)).

**Bande sectorielle Damodaran** (industrie retenue : *Steel*, snapshot au 2026-01-05) :

| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |
|---|---|---|---|---|
| Global | 1.129 | 0.834 | 0.929 | 719 |
| Europe | 0.906 | 0.692 | 0.855 | 57 |


## Synthèse globale

### MAE et biais par configuration (vs β endetté CIQ)

| Configuration | n | MAE | Biais moyen (répl. − CIQ) |
|---|---|---|---|
| CIQ répl. @indice local | 63 | 0.465 | -0.219 |
| CIQ répl. @^GSPC | 63 | 0.360 | -0.275 |
| CIQ répl. @^STOXX | 63 | 0.518 | -0.336 |
| CIQ répl. @règle US/Europe | 63 | 0.441 | -0.185 |
| CIQ répl. (meilleur indice) | 63 | 0.108 | -0.028 |
| 5a hebdo @local | 63 | 0.267 | 0.026 |
| 2a hebdo @local | 63 | 0.403 | -0.088 |
| Outil défaut @local | 63 | 0.915 | -0.496 |

### Indice identifié par société (config CIQ 5a quotidien)

Pour chaque société, l'indice (^GSPC / ^STOXX / indice local) dont le β 5a quotidien colle le mieux au β CIQ, et l'écart de R² associé.

| Société | ticker | β CIQ | R² CIQ | indice retenu | β | R² | règle US/Eu ? |
|---|---|---|---|---|---|---|---|
| Mueller Water Products, Inc. | MWA | 0.907 | 0.252 | ^GSPC | 0.989 | 0.301 | oui |
| Omega Flex, Inc. | OFLX | 0.772 | 0.109 | ^GSPC | 0.854 | 0.134 | oui |
| Savencia SA | SAVE.PA | 0.265 | 0.034 | ^STOXX | 0.273 | 0.035 | oui |
| Danone SA | BN.PA | 0.436 | 0.108 | ^STOXX | 0.430 | 0.108 | oui |
| Glanbia Plc | GL9.IR | 0.473 | 0.057 | ^STOXX | 0.462 | 0.055 | oui |
| Emmi AG | EMMN.SW | 0.346 | 0.059 | ^STOXX | 0.415 | 0.092 | oui |
| Fonterra Co-operative Group  | FCG.NZ | 0.156 | 0.006 | ^GSPC | 0.097 | 0.003 | non |
| Bega Cheese Limited | BGA.AX | 1.043 | 0.186 | ^AXJO | 0.893 | 0.152 | non |
| Geberit AG | GEBN.SW | 0.941 | 0.320 | ^STOXX | 1.013 | 0.374 | oui |
| Westlake Corporation | WLK | 1.004 | 0.219 | ^GSPC | 1.087 | 0.249 | oui |
| Advanced Drainage Systems, I | WMS | 1.004 | 0.219 | ^STOXX | 0.989 | 0.109 | non |
| Georg Fischer AG | GF.SW | 1.229 | 0.384 | ^STOXX | 1.296 | 0.409 | oui |
| Aalberts N.V. | AALB.AS | 1.550 | 0.446 | ^STOXX | 1.580 | 0.464 | oui |
| Genuit Group plc | GEN.L | 1.056 | 0.154 | ^FTSE | 1.040 | 0.156 | non |
| Wienerberger AG | WIE.VI | 1.356 | 0.349 | ^STOXX | 1.356 | 0.352 | oui |
| SAP | SAP.DE | 1.020 | 0.269 | ^STOXX | 1.019 | 0.269 | oui |
| SalesForce | CRM | 1.168 | 0.277 | ^GSPC | 1.253 | 0.328 | oui |
| ServiceNow | NOW | 1.388 | 0.289 | ^GSPC | 1.474 | 0.327 | oui |
| PTC | PTC | 0.952 | 0.272 | ^GSPC | 1.036 | 0.327 | oui |
| The Sage Group | SGE.L | 0.722 | 0.150 | ^STOXX | 0.635 | 0.125 | oui |
| Nemetschek | NEM.DE | 1.250 | 0.204 | ^STOXX | 1.252 | 0.207 | oui |
| Pegasystems | PEGA | 1.293 | 0.181 | ^GSPC | 1.379 | 0.206 | oui |
| Temenos | TEMN.SW | 1.113 | 0.133 | ^STOXX | 1.177 | 0.150 | oui |
| Kinaxis | KXS.TO | 0.851 | 0.169 | ^GSPC | 0.838 | 0.167 | non |
| Axway (74Software) | 74SW.PA | 0.328 | 0.026 | ^STOXX | 0.327 | 0.026 | oui |
| Worldline SA | WLN.PA | 1.557 | 0.093 | ^STOXX | 1.567 | 0.120 | oui |
| Nexi S.p.A. | NEXI.MI | 1.315 | 0.267 | ^STOXX | 1.333 | 0.276 | oui |
| CAB Payments Holdings | CABP.L | 0.553 | 0.014 | ^GSPC | 0.512 | 0.010 | non |
| Shift4 Payments, Inc. | FOUR | 1.595 | 0.228 | ^GSPC | 1.680 | 0.251 | oui |
| Block, Inc. | XYZ | 2.183 | 0.392 | ^GSPC | 2.270 | 0.412 | oui |
| Global Payments Inc. | GPN | 1.121 | 0.270 | ^GSPC | 1.206 | 0.311 | oui |
| Payal Holding Inc. | PYPL | 1.336 | 0.294 | ^GSPC | 1.422 | 0.329 | oui |
| NCR Voyix Corporation | VYX | 1.348 | 0.206 | ^GSPC | 1.433 | 0.263 | oui |
| Hipay Group SA | ALHYP.PA | 0.811 | 0.036 | ^STOXX | 0.816 | 0.037 | oui |
| FleetCor Technologies, Inc. | CPAY | 1.094 | 0.325 | ^GSPC | 1.180 | 0.380 | oui |
| Eiffage SA | FGR.PA | 0.413 | 0.075 | ^GSPC | 0.329 | 0.062 | non |
| Bouygues SA | EN.PA | 0.327 | 0.058 | ^GSPC | 0.237 | 0.041 | non |
| HOCHTIEF Aktiengesellschaft | HOT.DE | 0.558 | 0.083 | ^GSPC | 0.497 | 0.078 | non |
| Strabag SE | STR.VI | 0.369 | 0.034 | ^GSPC | 0.292 | 0.026 | non |
| Skanska AB (publ) | SKA-B.ST | 0.602 | 0.100 | ^GSPC | 0.461 | 0.085 | non |
| Vinci SA | DG.PA | 0.407 | 0.080 | ^GSPC | 0.327 | 0.067 | non |
| Peab AB (publ) | PEAB-B.ST | 0.669 | 0.099 | ^GSPC | 0.542 | 0.088 | non |
| AF Gruppen ASA | AFG.OL | 0.391 | 0.053 | ^STOXX | 0.443 | 0.065 | oui |
| Keller Group plc | KLR.L | 0.521 | 0.064 | ^GSPC | 0.408 | 0.046 | non |
| NCC Group plc | NCC.L | 0.432 | 0.037 | ^GSPC | 0.322 | 0.023 | non |
| Computacenter plc | CCC.L | 0.947 | 0.165 | ^FTSE | 0.934 | 0.168 | non |
| Econocom Group SE | ECONB.BR | 0.693 | 0.083 | ^STOXX | 0.693 | 0.084 | oui |
| CDW Corporation | CDW | 1.004 | 0.349 | ^GSPC | 1.089 | 0.418 | oui |
| ePlus inc. | PLUS | 0.978 | 0.214 | ^GSPC | 1.064 | 0.257 | oui |
| Kyndryl Holdings, Inc. | KD | 1.179 | 0.130 | ^GSPC | 1.335 | 0.156 | oui |
| DXC Technology Company | DXC | 1.194 | 0.209 | ^GSPC | 1.279 | 0.235 | oui |
| Atos SE | ATO.PA | 1.496 | 0.026 | ^GSPC | -1.499 | 0.000 | non |
| Unisys Corporation | UIS | 1.432 | 0.131 | ^GSPC | 1.518 | 0.145 | oui |
| Ricoh Company, Ltd. | 7752.T | 0.760 | 0.143 | ^N225 | 0.789 | 0.303 | non |
| Diebold Nixdorf, Incorporate | DBD | 0.450 | 0.068 | ^STOXX | 0.798 | 0.058 | non |
| Voestalpine AG | VOE.VI | 1.411 | 0.361 | ^STOXX | 1.412 | 0.366 | oui |
| Klöckner & Co SE | KCO.DE | 1.184 | 0.169 | ^STOXX | 1.189 | 0.172 | oui |
| Jacquet Metals | JCQ.PA | 1.022 | 0.194 | ^STOXX | 1.028 | 0.199 | oui |
| Reliance Inc. | RS | 0.750 | 0.205 | ^GSPC | 0.834 | 0.259 | oui |
| Russel Metals | RUS.TO | 0.782 | 0.236 | ^GSPC | 0.776 | 0.251 | non |
| Acerinox | ACX.MC | 1.277 | 0.377 | ^STOXX | 1.295 | 0.393 | oui |
| Outokumpu | OUT1V.HE | 1.352 | 0.289 | ^STOXX | 1.361 | 0.304 | oui |
| Salzgitter AG | SZG.DE | 1.776 | 0.217 | ^STOXX | 1.799 | 0.225 | oui |

**Règle « US→^GSPC, Europe→^STOXX » vérifiée pour 43/63 sociétés (68 %).**

### Diagnostic devise (local vs EUR-converti, β 5a quotidien vs ^STOXX)

| Société | devise | β CIQ | β local | R² local | β EUR | R² EUR | plus proche CIQ |
|---|---|---|---|---|---|---|---|
| Emmi AG | CHF | 0.346 | 0.415 | 0.092 | 0.369 | 0.070 | EUR |
| Geberit AG | CHF | 0.941 | 1.013 | 0.374 | 0.970 | 0.340 | EUR |
| Georg Fischer AG | CHF | 1.229 | 1.296 | 0.409 | 1.253 | 0.384 | EUR |
| Genuit Group plc | GBP | 1.056 | 1.114 | 0.228 | 1.146 | 0.225 | local |
| The Sage Group | GBP | 0.722 | 0.635 | 0.125 | 0.666 | 0.121 | EUR |
| Temenos | CHF | 1.113 | 1.177 | 0.150 | 1.131 | 0.137 | EUR |
| CAB Payments Holdings | GBP | 0.553 | 1.028 | 0.029 | 1.056 | 0.031 | local |
| Skanska AB (publ) | SEK | 0.602 | 1.166 | 0.367 | 1.176 | 0.353 | local |
| Peab AB (publ) | SEK | 0.669 | 1.200 | 0.293 | 1.210 | 0.286 | local |
| AF Gruppen ASA | NOK | 0.391 | 0.443 | 0.065 | 0.512 | 0.076 | local |
| Keller Group plc | GBP | 0.521 | 0.830 | 0.131 | 0.869 | 0.131 | local |
| NCC Group plc | GBP | 0.432 | 0.794 | 0.094 | 0.834 | 0.097 | local |
| Computacenter plc | GBP | 0.947 | 1.019 | 0.250 | 1.051 | 0.239 | local |

**Verdict devise : cours locaux plus proches du CIQ pour 8 société(s), EUR-converti pour 5.** Voir interprétation ci-dessous.
