## ADDED Requirements

### Requirement: Reporte de impacto de features desglosado por categoría de nota
El sistema SHALL calcular, además del reporte de impacto SHAP global, una tabla de impacto por feature separada para cada valor de `categoria_nota`, usando el mismo modelo final entrenado sobre el 100% del dataset (sin reentrenar por categoría).

#### Scenario: Tabla de impacto por categoría generada tras el entrenamiento
- **WHEN** el entrenamiento del modelo baseline completa exitosamente
- **THEN** el sistema genera, además de la tabla de impacto global, una tabla con una fila por combinación `(categoria_nota, feature)` con su `mean_abs_shap` y `views_multiplier` calculados solo sobre las filas de esa categoría
- **AND** esa tabla queda persistida junto al modelo entrenado y al reporte global, fuera de control de versiones

#### Scenario: Reporte global no se modifica
- **WHEN** se agrega el desglose por categoría
- **THEN** la tabla de impacto global (`feature_impact.csv`) sigue calculándose y persistiéndose exactamente igual que antes

#### Scenario: Categoría con pocas filas no rompe el cálculo
- **WHEN** una categoría tiene muy pocas notas en el dataset de entrenamiento
- **THEN** el sistema calcula igual su tabla de impacto SHAP para esa categoría, sin excluirla ni fallar, aunque el resultado tenga más varianza
