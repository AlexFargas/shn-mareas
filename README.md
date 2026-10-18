# shn-mareas

Datos públicos del **Servicio de Hidrografía Naval (SHN)** para el puerto de **San Fernando**, en JSON, para la app [wind-buddy-ba](https://wind-buddy-ba.lovable.app/).

- `marea.json`: últimas 48 alturas medidas (horarias) y el pronóstico mareológico oficial del Río de la Plata interior (pleamares/bajamares corregidas por viento, texto de corrección y perspectiva).
- `fetch_shn.py`: script que lo genera (Python, solo biblioteca estándar).
- `.github/workflows/actualizar.yml`: GitHub Actions lo ejecuta cada 30 minutos y commitea el resultado si cambió.

Fuentes: https://www.hidro.gob.ar/oceanografia/AlturasHorarias.asp y https://www.hidro.gob.ar/oceanografia/pronostico.asp
