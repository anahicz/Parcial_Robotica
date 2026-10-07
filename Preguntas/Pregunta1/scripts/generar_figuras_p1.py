import sys
import textwrap
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def bool_value(v):
    if isinstance(v, str):
        return v.strip().lower() in {'true', '1', 'si', 'sí', 'yes'}
    return bool(v)


def main():
    if len(sys.argv) != 2:
        print('Uso: python3 scripts/generar_figuras_p1.py <resultados.csv>')
        raise SystemExit(1)

    ruta = Path(sys.argv[1])
    df = pd.read_csv(ruta)
    salida = ruta.parent
    escenario = str(df['escenario'].iloc[0]) if 'escenario' in df else ruta.stem

    metricas = ['Exactitud total', 'Acción', 'Objeto', 'Color', 'Prioridad', 'Permitido']
    laya = [
        df['laya_correcto_total'].mean() * 100,
        df['laya_ok_accion'].mean() * 100,
        df['laya_ok_objeto'].mean() * 100,
        df['laya_ok_color'].mean() * 100,
        df['laya_ok_prioridad'].mean() * 100,
        df['laya_ok_permitido'].mean() * 100,
    ]
    kw = [
        df['kw_correcto_total'].mean() * 100,
        df['kw_ok_accion'].mean() * 100,
        df['kw_ok_objeto'].mean() * 100,
        df['kw_ok_color'].mean() * 100,
        df['kw_ok_prioridad'].mean() * 100,
        df['kw_ok_permitido'].mean() * 100,
    ]

    x = range(len(metricas))
    width = 0.35
    fig, ax = plt.subplots(figsize=(12, 7))
    b1 = ax.bar([i - width / 2 for i in x], laya, width=width, label='LAYA')
    b2 = ax.bar([i + width / 2 for i in x], kw, width=width, label='Keywords')
    ax.set_xticks(list(x))
    ax.set_xticklabels(metricas, rotation=20)
    ax.set_ylabel('Porcentaje (%)')
    ax.set_ylim(0, 112)
    ax.set_title(f'Comparación de exactitud: LAYA vs. Keywords — Escenario {escenario}')
    ax.legend(loc='upper left')
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1,
                    f'{b.get_height():.0f}%', ha='center', va='bottom', fontsize=9)
    fig.tight_layout()
    fig.savefig(salida / f'comparacion_resumen_{escenario}.png', dpi=200)
    plt.close(fig)

    def compacto(r, prefijo):
        return (
            f"{r[f'{prefijo}_accion']} | {r[f'{prefijo}_objeto']} | "
            f"{r[f'{prefijo}_color']} | p{r[f'{prefijo}_prioridad']} | "
            f"permitido={'sí' if bool_value(r[f'{prefijo}_permitido']) else 'no'}"
        )

    tabla = df.copy()
    tabla['Esperado'] = tabla.apply(
        lambda r: (
            f"{r['esperado_accion']} | {r['esperado_objeto']} | "
            f"{r['esperado_color']} | p{r['esperado_prioridad']} | "
            f"permitido={'sí' if bool_value(r['esperado_permitido']) else 'no'}"
        ), axis=1
    )
    tabla['LAYA'] = tabla.apply(lambda r: compacto(r, 'laya'), axis=1)
    tabla['Keywords'] = tabla.apply(lambda r: compacto(r, 'kw'), axis=1)
    tabla['OK LAYA'] = tabla['laya_correcto_total'].map(lambda v: 'Sí' if bool_value(v) else 'No')
    tabla['OK KW'] = tabla['kw_correcto_total'].map(lambda v: 'Sí' if bool_value(v) else 'No')

    def guardar(inicio, fin):
        t = tabla.iloc[inicio:fin][['id', 'frase', 'Esperado', 'LAYA', 'Keywords', 'OK LAYA', 'OK KW']].copy()
        t.columns = ['ID', 'Frase', 'Esperado', 'LAYA', 'Keywords', 'OK LAYA', 'OK KW']
        for c in ['Frase', 'Esperado', 'LAYA', 'Keywords']:
            t[c] = t[c].astype(str).map(lambda s: '\n'.join(textwrap.wrap(s, width=34)))

        fig, ax = plt.subplots(figsize=(22, 16))
        ax.axis('off')
        tb = ax.table(cellText=t.values, colLabels=t.columns, loc='center', cellLoc='left')
        tb.auto_set_font_size(False)
        tb.set_fontsize(7.5)
        tb.scale(1, 1.75)
        ax.set_title(f'Frases ejecutadas {inicio + 1}–{fin}: LAYA vs. Keywords — {escenario}', pad=18)
        fig.tight_layout()
        fig.savefig(salida / f'comparacion_frases_{escenario}_{inicio + 1:02d}_{fin:02d}.png',
                    dpi=180, bbox_inches='tight')
        plt.close(fig)

    guardar(0, 25)
    guardar(25, 50)

    print(f'Figuras guardadas en: {salida}')


if __name__ == '__main__':
    main()
