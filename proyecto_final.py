import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
import os

# ══════════════════════════════════════════════════════════════
# CONFIGURACIONES DE ENTORNO GLOBALES
# ══════════════════════════════════════════════════════════════
PALLET_ESTANDAR = {
    'largo':       1.219,    # m
    'ancho':       1.016,    # m
    'alto_madera': 0.1524,   # m
    'peso_vacio':  25.0,     # kg
}

RESTRICCIONES = {
    'altura_max':      1.800,   # m
    'peso_max_pallet': 1000.0,  # kg
}

CARPETA_IMAGENES = "imagenes_pallet"

# ══════════════════════════════════════════════════════════════
# MOTOR GRÁFICO Y ESTRATEGIAS 
# ══════════════════════════════════════════════════════════════
def iso(x, y, z):
    return (x - y) * 0.866025, (x + y) * 0.5 + z

def dibujar_cara(ax, vertices_3d, color, borde="#2C3E50", zorder=1):
    puntos_2d = [iso(x, y, z) for x, y, z in vertices_3d]
    ax.fill([p[0] for p in puntos_2d], [p[1] for p in puntos_2d], color=color, edgecolor=borde, lw=1.0, alpha=1.0, zorder=zorder)

def dibujar_caja_3d(ax, x, y, z, l, a, h, color_principal, zorder=10):
    dibujar_cara(ax, [(x,y,z), (x,y+a,z), (x,y+a,z+h), (x,y,z+h)], "#8FAFC5", borde="#2C3E50", zorder=zorder)
    dibujar_cara(ax, [(x,y,z), (x+l,y,z), (x+l,y,z+h), (x,y,z+h)], color_principal, borde="#2C3E50", zorder=zorder)
    dibujar_cara(ax, [(x,y,z+h), (x+l,y,z+h), (x+l,y+a,z+h), (x,y+a,z+h)], "#D8ECF8", borde="#2C3E50", zorder=zorder)

def capa_horizontal(pl, pa, cl, ca, z, inv):
    nx, ny = int(pl // cl), int(pa // ca)
    if nx == 0 or ny == 0: return []
    ox, oy = (pl - nx*cl)/2, (pa - ny*ca)/2
    cajas = []
    for f in range(ny):
        for c in range(nx):
            x = ox + ((nx - 1 - c)*cl if inv else c*cl)
            y = oy + ((ny - 1 - f)*ca if inv else f*ca)
            if x >= 0 and y >= 0 and (x + cl) <= pl and (y + ca) <= pa:
                cajas.append({'x': x, 'y': y, 'z': z, 'l': cl, 'a': ca, 'color': "#D8E4EC"})
    return cajas

def capa_splitrow(pl, pa, cl, ca, z, alternar):
    """Patrón ENTRELAZADO con ROTACIÓN 90° - VISIBLE y LIMPIO"""
    
    if not alternar:
        # CAPAS IMPARES: Cajas en dirección normal (cl x ca)
        nx = int(pl // cl)
        ny = int(pa // ca)
        largo_caja = cl
        ancho_caja = ca
    else:
        # CAPAS PARES: Cajas ROTADAS 90° (ca x cl) - DIFERENTE VISUALMENTE
        nx = int(pl // ca)
        ny = int(pa // cl)
        largo_caja = ca
        ancho_caja = cl
    
    if nx == 0 or ny == 0:
        return []
    
    ox = (pl - nx*largo_caja) / 2
    oy = (pa - ny*ancho_caja) / 2
    
    cajas = []
    for f in range(ny):
        for c in range(nx):
            x = ox + c*largo_caja
            y = oy + f*ancho_caja
            cajas.append({'x': x, 'y': y, 'z': z, 'l': largo_caja, 'a': ancho_caja, 'color': "#D8E4EC"})
    
    return cajas

def verificar_soporte_total(capa_base, capa_superior, tolerancia=10.0):
    for caja_sup in capa_superior:
        x1_s, y1_s = caja_sup['x'], caja_sup['y']
        x2_s, y2_s = caja_sup['x'] + caja_sup['l'], caja_sup['y'] + caja_sup['a']
        esquinas = [
            (x1_s + tolerancia, y1_s + tolerancia),
            (x2_s - tolerancia, y1_s + tolerancia),
            (x1_s + tolerancia, y2_s - tolerancia),
            (x2_s - tolerancia, y2_s - tolerancia)
        ]
        for px, py in esquinas:
            sobre_suelo_firme = False
            for caja_inf in capa_base:
                x1_i, y1_i = caja_inf['x'], caja_inf['y']
                x2_i, y2_i = caja_inf['x'] + caja_inf['l'], caja_inf['y'] + caja_inf['a']
                if (x1_i <= px <= x2_i) and (y1_i <= py <= y2_i):
                    sobre_suelo_firme = True
                    break
            if not sobre_suelo_firme:
                return False
    return True

# ══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════
def optimizar_y_dibujar_pallet(box, pallet, trip, ruta_imagen=None, sku=None, descripcion=None):
    cl, ca, ch = box['largo'] * 1000, box['ancho'] * 1000, box['alto'] * 1000
    ph = pallet['alto_madera'] * 1000
    pl_base = pallet['largo'] * 1000
    pa_base = pallet['ancho'] * 1000

    es_doble_pallet = cl > (1219 + 50) or ca > (1016 + 50)

    if es_doble_pallet:
        pl_real = pa_base * 2
        pa_real = pl_base
        peso_vacio_tarima = pallet['peso_vacio'] * 2
        peso_max_permitido = trip['peso_max_pallet'] * 2
    else:
        pl_real = pl_base
        pa_real = pa_base
        peso_vacio_tarima = pallet['peso_vacio']
        peso_max_permitido = trip['peso_max_pallet']

    pl_max = pl_real 
    pa_max = pa_real

    # ASIGNACIÓN DE LAS NUEVAS ESTRATEGIAS REESCRITAS
    estrategias = {
        'Splitrow Pattern (Filas Divididas)': lambda piso, z: capa_splitrow(pl_max, pa_max, cl, ca, z, piso % 2 != 0),
        'Apilado Columnar Estructural (Alineado)': lambda piso, z: capa_horizontal(pl_max, pa_max, cl, ca, z, False),
    }

    mejor_estrategia = None
    max_cajas = 0
    cajas_finales = []

    for nombre, funcion_capa in estrategias.items():
        cajas_estrategia = []
        capas_por_piso = []
        piso = 0
        peso_acumulado = peso_vacio_tarima
        altura_acumulada = ph
        while True:
            z_pos = ph + (piso * ch)
            if (altura_acumulada + ch) > (trip['altura_max'] * 1000): break
            
            nuevas_cajas = funcion_capa(piso, z_pos)
            if not nuevas_cajas: break
            
            if piso > 0 and nombre != 'Apilado Columnar Estructural (Alineado)':
                capa_anterior = capas_por_piso[-1]
                tiene_soporte = verificar_soporte_total(capa_anterior, nuevas_cajas, tolerancia=10.0)
                if not tiene_soporte:
                    nuevas_cajas = estrategias['Apilado Columnar Estructural (Alineado)'](piso, z_pos)

            peso_capa = len(nuevas_cajas) * box['peso']
            if (peso_acumulado + peso_capa) > peso_max_permitido: break

            cajas_estrategia.extend(nuevas_cajas)
            capas_por_piso.append(nuevas_cajas)
            peso_acumulado += peso_capa
            altura_acumulada += ch
            piso += 1

        # LOGICA INGENIERIL DE DESEMPATE: Si empatan en cantidad de cajas, priorizamos Splitrow por su amarre y uniformidad
        if len(cajas_estrategia) > max_cajas or (len(cajas_estrategia) == max_cajas and nombre == 'Splitrow Pattern (Filas Divididas)'):
            max_cajas = len(cajas_estrategia)
            mejor_estrategia = nombre
            cajas_finales = cajas_estrategia

    for c in cajas_finales:
        c['x'] -= 25
        c['y'] -= 25

    niveles = len(set([c['z'] for c in cajas_finales]))
    cajas_por_cama = max_cajas // niveles if niveles > 0 else 0
    alt_final_real = ph + (niveles * ch)
    p_bruto = (len(cajas_finales) * box['peso']) + peso_vacio_tarima

    fig = plt.figure(figsize=(14, 14), facecolor="#FFFFFF")
    ax_header  = plt.subplot2grid((12, 6), (0, 0), rowspan=1, colspan=6, facecolor="#FFFFFF")
    ax_3d      = plt.subplot2grid((12, 6), (1, 0), rowspan=6, colspan=4, facecolor="#FFFFFF")
    ax_2d_1    = plt.subplot2grid((12, 6), (7, 0), rowspan=5, colspan=2, facecolor="#FFFFFF")
    ax_2d_2    = plt.subplot2grid((12, 6), (7, 2), rowspan=5, colspan=2, facecolor="#FFFFFF")
    ax_sidebar = plt.subplot2grid((12, 6), (1, 4), rowspan=11, colspan=2, facecolor="#FFFFFF")

    for ax in [ax_header, ax_3d, ax_2d_1, ax_2d_2, ax_sidebar]:
        ax.axis("off")
        if ax in [ax_3d, ax_2d_1, ax_2d_2]: ax.set_aspect("equal")

    x_min, x_max = -pa_real * 0.866 - 100, pl_real * 0.866 + 100
    y_min, y_max = -100, (pl_real + pa_real) * 0.5 + (trip['altura_max'] * 1000) + 100
    ax_3d.set_xlim(x_min, x_max)
    ax_3d.set_ylim(y_min, y_max)
    ax_2d_1.set_xlim(-50, pl_real + 50)
    ax_2d_1.set_ylim(-50, pa_real + 50)
    ax_2d_2.set_xlim(-50, pl_real + 50)
    ax_2d_2.set_ylim(-50, pa_real + 50)

    ax_header.text(0.0, 0.6, "FICHA TECNICA", fontsize=18, weight='bold', color="#0F172A")
    ax_header.text(0.0, 0.2, f"SKU CONTROL: {sku if sku else 'N/D'}  |  DESCRIPCIÓN: {descripcion if descripcion else 'N/D'}", fontsize=11, color="#475569", weight='bold')

    if es_doble_pallet:
        w_p = pa_base
        dibujar_cara(ax_3d, [(0,0,0), (0,pa_real,0), (0,pa_real,ph), (0,0,ph)], "#A47C38", zorder=1)
        dibujar_cara(ax_3d, [(0,0,0), (w_p,0,0), (w_p,0,ph), (0,0,ph)], "#C69C54", zorder=1)
        dibujar_cara(ax_3d, [(0,0,ph), (w_p,0,ph), (w_p,pa_real,ph), (0,pa_real,ph)], "#E4BC74", zorder=2)
        dibujar_cara(ax_3d, [(w_p,0,0), (pl_real,0,0), (pl_real,0,ph), (w_p,0,ph)], "#C69C54", zorder=1)
        dibujar_cara(ax_3d, [(w_p,0,ph), (pl_real,0,ph), (pl_real,pa_real,ph), (w_p,pa_real,ph)], "#E4BC74", zorder=2)
    else:
        dibujar_cara(ax_3d, [(0,0,0), (0,pa_real,0), (0,pa_real,ph), (0,0,ph)], "#A47C38", zorder=1)
        dibujar_cara(ax_3d, [(0,0,0), (pl_real,0,0), (pl_real,0,ph), (0,0,ph)], "#C69C54", zorder=1)
        dibujar_cara(ax_3d, [(0,0,ph), (pl_real,0,ph), (pl_real,pa_real,ph), (0,pa_real,ph)], "#E4BC74", zorder=2)

    cajas_finales.sort(key=lambda c: (c['z'], -(c['x'] + c['l']/2 + c['y'] + c['a']/2), -(c['x'] + c['l']/2)))

    for idx, c in enumerate(cajas_finales):
        dibujar_caja_3d(ax_3d, c['x'], c['y'], c['z'], c['l'], c['a'], ch, c['color'], zorder=10 + idx)

    #tipo_tarima_str = "DOBLE TARIMA" if es_doble_pallet else "TARIMA SIMPLE"
    #ax_3d.text((x_min + x_max)/2, y_min + 50, f"Vista 3D ({tipo_tarima_str})\nAltura Real: {alt_final_real/1000:.2f}m", ha='center', fontsize=11, weight='bold', color="#1E293B")

    # PLANOS 2D ASIGNADOS DE MANERA CORRECTA SEGÚN EL PISO CORRESPONDIENTE
    for ax, piso_id, titulo in [(ax_2d_1, 0, "PLANO CAPA IMPAR (Base)"), (ax_2d_2, 1, "PLANO CAPA PAR")]:
        if es_doble_pallet:
            w_p = pa_base
            ax.fill([0, w_p, w_p, 0], [0, 0, pa_real, pa_real], color="#E4BC74", alpha=0.25, edgecolor="#A47C38", lw=1.5, hatch='/')
            ax.fill([w_p, pl_real, pl_real, w_p], [0, 0, pa_real, pa_real], color="#E4BC74", alpha=0.25, edgecolor="#A47C38", lw=1.5, hatch='\\')
        else:
            ax.fill([0, pl_real, pl_real, 0], [0, 0, pa_real, pa_real], color="#E4BC74", alpha=0.3, edgecolor="#A47C38", lw=1.5)
        z_nivel = ph + (piso_id * ch)
        cajas_nivel = [c for c in cajas_finales if abs(c['z'] - z_nivel) < 1]
        for c in cajas_nivel:
            ax.fill([c['x'], c['x'] + c['l'], c['x'] + c['l'], c['x']], [c['y'], c['y'], c['y'] + c['a'], c['y'] + c['a']], color=c['color'], edgecolor="#2C3E50", lw=1.2)
        ax.set_title(titulo, fontsize=11, weight='bold', color="#0F172A", pad=10)

    ax_sidebar.set_xlim(0, 1)
    ax_sidebar.set_ylim(0, 1)
    def crear_seccion(y, titulo):
        ax_sidebar.add_patch(Rectangle((0, y), 1, 0.035, facecolor="#0F172A", edgecolor="none"))
        ax_sidebar.text(0.03, y + 0.008, titulo, fontsize=10, weight='bold', color="#FFFFFF")
    def crear_fila(y, campo, valor):
        ax_sidebar.text(0.03, y, campo, fontsize=10, color="#475569")
        ax_sidebar.text(0.97, y, valor, fontsize=10, weight='bold', color="#0F172A", ha='right')
        ax_sidebar.add_patch(Rectangle((0, y-0.01), 1, 0.001, facecolor="#E2E8F0", edgecolor="none"))

    crear_seccion(0.92, "ESPECIFICACIONES CAJA")
    crear_fila(0.88, "Dimensiones:", f"{box['largo']:.2f}x{box['ancho']:.2f}x{box['alto']:.2f} m")
    crear_fila(0.83, "Peso Unitario:", f"{box.get('peso', 0)} kg")
    crear_seccion(0.74, "ESPECIFICACIONES PALLET")
    crear_fila(0.70, "Medidas Tarima:", f"{pl_real/1000:.2f} x {pa_real/1000:.2f} m")
    crear_fila(0.65, "Alto Madera:", f"{pallet['alto_madera']:.3f} m")
    crear_fila(0.60, "Peso Vacío:", f"{peso_vacio_tarima:.1f} kg")
    crear_seccion(0.51, "DETALLES PALlET")
    crear_fila(0.47, "Cajas por Capa:", f"{cajas_por_cama} ud")
    crear_fila(0.42, "Número de Capas:", f"{niveles} niveles")
    crear_fila(0.37, "Total Cajas:", f"{len(cajas_finales)} ud")
    crear_seccion(0.23, "RESUMEN LOGÍSTICO")
    crear_fila(0.19, "Peso Carga Neto:", f"{(len(cajas_finales)*box['peso']):.1f} kg")
    crear_fila(0.14, "Peso Bruto Pallet:", f"{p_bruto:.1f} kg")
    crear_fila(0.09, "Altura Total:", f"{alt_final_real/1000:.2f} m")

    if ruta_imagen:
        plt.savefig(ruta_imagen, dpi=130, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

    return {
        'total_cajas':    len(cajas_finales),
        'cajas_por_cama': cajas_por_cama,
        'niveles':        niveles,
        'peso_total_kg':  round(p_bruto, 2),
        'alto_total_m':   round(alt_final_real / 1000, 3),
        'largo_pallet_m': round(pl_real / 1000, 3),
        'ancho_pallet_m': round(pa_real / 1000, 3),
        'estrategia':      mejor_estrategia,
    }

# ══════════════════════════════════
# PROCESAMIENTO DESDE EXCEL 
# ═════════════════════════════════
def procesar_excel(archivo_entrada, archivo_salida=None):
    os.makedirs(CARPETA_IMAGENES, exist_ok=True)
    df = pd.read_excel(archivo_entrada)
    print(f"  {len(df)} artículos encontrados en {archivo_entrada}\n")
    
    filas_resultados = []

    for idx, row in df.iterrows():
        # Mapeo de datos
        sku = str(row['SKU'])
        desc = row['Descripcion']
        box = {
            'largo': row['MP_Largo'] , 
            'ancho': row['MP_Ancho'] , 
            'alto': row['MP_Alto'] , 
            'peso': row['MP_Peso']
        }
        
        ruta_img = os.path.join(CARPETA_IMAGENES, f"Pallet_{sku}.png")
        
        # Ejecutar optimización y dibujo
        metricas = optimizar_y_dibujar_pallet(
            box=box, 
            pallet=PALLET_ESTANDAR, 
            trip=RESTRICCIONES, 
            ruta_imagen=ruta_img, 
            sku=sku, 
            descripcion=desc
        )
        
        # Guardar resultados en una fila
        fila = row.to_dict()
        fila.update(metricas)
        fila['Ruta_Imagen'] = ruta_img
        filas_resultados.append(fila)
        
        print(f"Pallet generado: {sku}")

    # Guardar reporte Excel final
    df_salida = pd.DataFrame(filas_resultados)
    nombre_xlsx = "Reporte_Estiba_Final.xlsx"
    df_salida.to_excel(nombre_xlsx, index=False)
    print(f"\n✅ Proceso completado. Reporte guardado como: {nombre_xlsx}")

if __name__ == "__main__":
    procesar_excel('tVolumetria_Vidri_ElSalvador.xlsx')
    pass