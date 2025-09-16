# Scraping Completo - Sistema Nacional de Indicadores

Este script automatiza la extracción de metadatos de indicadores del Sistema Nacional de Indicadores de México.

## 🚀 Características

- **Extracción de URLs**: Utiliza Selenium para extraer todos los enlaces de metadatos de los indicadores
- **Scraping de metadatos**: Usa Playwright para procesar cada página de metadatos de forma asíncrona
- **Control de concurrencia**: Procesa hasta 10 páginas simultáneamente
- **Manejo de errores**: Reintentos automáticos y registro de errores
- **Guardado de progreso**: Guarda el progreso parcial para poder reanudar en caso de interrupción
- **Exportación a Excel**: Genera archivos XLSX con todos los metadatos extraídos

## 📋 Requisitos

```bash
pip install -r requirements.txt
playwright install
```

## 🛠️ Instalación

1. Clona o descarga el proyecto
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Instala los navegadores de Playwright:
   ```bash
   playwright install
   ```

## 📊 Uso

Ejecuta el script completo:
```bash
python3 scraping_completo.py
```

El script realizará dos procesos secuenciales:

1. **Extracción de URLs**: Abre el sitio web y extrae todos los enlaces de metadatos
2. **Scraping de metadatos**: Procesa cada URL y extrae la información de los indicadores

## 📁 Estructura de archivos

- `scraping_completo.py` - Script principal
- `requirements.txt` - Dependencias de Python
- `metadatos_links.txt` - URLs extraídas (generado automáticamente)
- `resultados/` - Directorio con los archivos Excel generados
  - `metadatos_indicadores_YYYYMMDD_HHMMSS.xlsx` - Archivo con timestamp
  - `metadatos_indicadores_completo.xlsx` - Último archivo completo

## ⚙️ Configuración

Puedes ajustar estos parámetros en el script:

- `MAX_CONCURRENT_PAGES`: Número máximo de páginas simultáneas (default: 10)
- `REQUEST_TIMEOUT`: Timeout para las solicitudes (default: 60000 ms)
- `RETRY_ATTEMPTS`: Intentos de reintento por URL (default: 3)

## 🔄 Reanudar proceso

Si el proceso se interrumpe, el script puede reanudar desde donde quedó gracias al archivo de progreso parcial.

## 📊 Columnas del Archivo Excel

El archivo Excel generado incluye las siguientes columnas:
- Índice
- URL
- Nombre del Indicador
- Tema/Subsistema
- Objetivo
- Definición
- Unidad de medida
- Cobertura geográfica
- Periodicidad
- Periodo de referencia
- Oportunidad
- Cobertura temporal
- Estándares o recomendaciones
- Observaciones
- Fuente/Proyecto
- Variable
- IIN

## ⚠️ Notas

- Se requiere conexión a internet
- El proceso completo puede tomar varios minutos dependiendo del número de indicadores
- Se recomienda ejecutar en un entorno con buena conexión
- Los resultados se guardan automáticamente en el directorio `resultados/`

## Licencia

Este proyecto está licenciado bajo la [Licencia MIT](https://opensource.org/licenses/MIT).

Copyright (c) 2024 SLV

Proyecto desarrollado para el Instituto Nacional de Estadística y Geografía (INEGI).