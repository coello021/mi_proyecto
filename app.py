import streamlit as st
import pandas as pd
import proyecto_final as pf
import zipfile
import os
import uuid
import tempfile
import shutil
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LA PÁGINA
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Generador de Fichas de Pallets",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════
# ESTILOS PERSONALIZADOS
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div class="header-container">
    <h1>📦 Generador de Fichas Técnicas de Pallets</h1>
    <p>Carga tu archivo Excel y genera automáticamente fichas técnicas optimizadas de estiba con visualización 3D</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# SIDEBAR - INFORMACIÓN
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 📋 Instrucciones")
    st.info("""
    **Paso 1:** Carga tu archivo Excel con los datos de productos
    
    **Paso 2:** El sistema procesará y calculará la estiba óptima
    
    **Paso 3:** Descarga el ZIP con imágenes y reportes
    
    **Columnas requeridas:**
    - SKU
    - Descripcion
    - MP_Largo (metros)
    - MP_Ancho (metros)
    - MP_Alto (metros)
    - MP_Peso (kg)
    """)
    
    st.markdown("---")
    st.markdown("### ⚙️ Configuración")
    altura_maxima = st.slider("Altura máxima (m)", 1.0, 2.5, 1.8, 0.1)
    peso_maximo = st.slider("Peso máximo (kg)", 500, 1500, 1000, 50)
    
    st.markdown("---")
    st.markdown("### 📊 Estadísticas")
    st.caption("Información del proceso")

# ═══════════════════════════════════════════════════════════════
# ÁREA PRINCIPAL
# ═══════════════════════════════════════════════════════════════

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📥 Carga tu archivo Excel")
    st.markdown("""
    <div class="info-box">
    El archivo debe contener las columnas: <b>SKU, Descripcion, MP_Largo, MP_Ancho, MP_Alto, MP_Peso</b>
    </div>
    """, unsafe_allow_html=True)
    
    archivo_excel = st.file_uploader(
        "Selecciona tu archivo Excel",
        type=['xlsx', 'xls'],
        help="Formato: .xlsx o .xls"
    )

with col2:
    st.markdown("### 📈 Vista previa")
    if archivo_excel:
        try:
            df_preview = pd.read_excel(archivo_excel, nrows=3)
            st.dataframe(df_preview, use_container_width=True, height=150)
        except Exception as e:
            st.error(f"Error al leer: {e}")

# ═══════════════════════════════════════════════════════════════
# PROCESAMIENTO
# ═══════════════════════════════════════════════════════════════

if archivo_excel:
    st.markdown("---")
    
    # Validar columnas
    try:
        df = pd.read_excel(archivo_excel)
        columnas_requeridas = ['SKU', 'Descripcion', 'MP_Largo', 'MP_Ancho', 'MP_Alto', 'MP_Peso']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            st.error(f"❌ Columnas faltantes: {', '.join(columnas_faltantes)}")
        else:
            st.success(f"✅ Archivo válido - {len(df)} productos detectados")
            
            # Botón para procesar
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                procesar_btn = st.button("🚀 Procesar", use_container_width=True)
            with col2:
                st.caption("")
            
            if procesar_btn:
                with st.spinner("⏳ Procesando... esto puede tomar un momento"):
                    try:
                        # Actualizar configuración
                        pf.RESTRICCIONES['altura_max'] = altura_maxima
                        pf.RESTRICCIONES['peso_max_pallet'] = peso_maximo
                        
                        # Procesar Excel
                        # Crear ID único para este usuario/sesión
                        session_id = str(uuid.uuid4())[:8]
                        carpeta_temp = f"temp_pallet_{session_id}"
                        nombre_reporte = f"Reporte_Pallets_{session_id}.xlsx"
                        
                        # Procesar con carpeta aislada
                        carpeta_imagenes, archivo_salida = pf.procesar_excel(
                            archivo_excel.name,
                            carpeta_imagenes=carpeta_temp,
                            archivo_salida=nombre_reporte
                            )
                            
                        
                        # Crear ZIP
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre_zip = f"Reporte_Pallets_{timestamp}.zip"
                        
                        # Limpiar ZIP anterior si existe
                        if os.path.exists(nombre_zip):
                            os.remove(nombre_zip)
                        
                        with zipfile.ZipFile(nombre_zip, 'w', zipfile.ZIP_DEFLATED) as z:
                            # Agregar imágenes
                            if os.path.exists(carpeta_imagenes):
                                for root, dirs, files in os.walk(carpeta_imagenes):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        arcname = os.path.relpath(file_path, '.')
                                        z.write(file_path, arcname)
                            
                            # Agregar reporte Excel
                            if os.path.exists(archivo_salida):
                                z.write(archivo_salida)
                        
                        # Mostrar éxito
                        st.markdown("""
                        <div class="success-box">
                        <h3>✅ ¡Proceso completado exitosamente!</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Leer reporte para mostrar estadísticas
                        df_reporte = pd.read_excel(archivo_salida)
                        
                        # Estadísticas
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("📦 Total SKUs", len(df_reporte))
                        with col2:
                            st.metric("📋 Total Cajas", int(df_reporte['total_cajas'].sum()))
                        with col3:
                            st.metric("⚖️ Peso Total (kg)", f"{df_reporte['peso_total_kg'].sum():.1f}")
                        with col4:
                            st.metric("📊 Capas Promedio", f"{df_reporte['niveles'].mean():.1f}")
                        
                        # Tabla de resultados
                        st.markdown("### 📊 Resumen de resultados")
                        df_display = df_reporte[[
                            'SKU', 'Descripcion', 'total_cajas', 'cajas_por_cama', 
                            'niveles', 'peso_total_kg', 'alto_total_m', 'estrategia'
                        ]].copy()
                        
                        st.dataframe(df_display, use_container_width=True, height=400)
                        
                        # Descarga
                        st.markdown("---")
                        st.markdown("### 📥 Descarga tu reporte")
                        
                        with open(nombre_zip, 'rb') as f:
                            st.download_button(
                                label="📦 Descargar ZIP completo",
                                data=f,
                                file_name=nombre_zip,
                                mime="application/zip",
                                use_container_width=True
                            )
                        
                        # Limpiar archivos temporales
                        if os.path.exists(carpeta_imagenes):
                            shutil.rmtree(carpeta_imagenes)
                        if os.path.exists(archivo_salida):
                            os.remove(archivo_salida)
                        
                    except Exception as e:
                        st.error(f"❌ Error durante el procesamiento: {str(e)}")
                        st.caption("Verifica que el archivo tenga el formato correcto")
    
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")

# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #999; padding: 2rem 0;'>
    <p>🏭 Generador de Fichas Técnicas de Pallets v1.0</p>
    <p style='font-size: 0.85rem;'>Optimización automática de estiba con visualización 3D</p>
</div>
""", unsafe_allow_html=True)
