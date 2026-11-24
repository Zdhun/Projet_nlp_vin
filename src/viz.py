"""Figures Plotly à partir des résultats et des profils du moteur."""

from collections.abc import Sequence
from html import escape
from textwrap import wrap

import plotly.graph_objects as go

from .explain import SentenceAnalysis
from .reference import load_blocks


BORDEAUX = "#6b1430"
PROFILE_BLUE = "#465774"
GRID = "#e5e5ea"
BLOCK_AXIS = {
    "fruit": "Fruité",
    "spice_oak": "Boisé<br>Épicé",
    "floral_mineral": "Floral",
    "structure": "Structure",
    "pairing": "Accords",
}


def _figure(*traces, **layout) -> go.Figure:
    """Applique la palette de l'interface et laisse la largeur au conteneur."""
    figure = go.Figure(data=traces)
    figure.update_layout(
        template="none",
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        separators=", ",
        font=dict(color="#1d1d1f", family="system-ui, sans-serif", size=12),
        **layout,
    )
    return figure


def radar_chart(item: dict) -> go.Figure:
    """Superpose les cosinus de couverture du profil utilisateur et du premier vin."""
    blocks = load_blocks()
    names = [block["name_fr"] for block in blocks]
    labels = [BLOCK_AXIS[block["id"]] for block in blocks]

    # Répète le premier axe à la fin pour fermer les deux polygones.
    traces = []
    for profile, name, color, fill, dash in (
        (item["user_block_profile"], "Votre profil", PROFILE_BLUE, "rgba(70,87,116,0.10)", "dash"),
        (item["wine_block_profile"], "Vin classé 1er", BORDEAUX, "rgba(107,20,48,0.13)", "solid"),
    ):
        scores = [float(profile[block]) for block in names]
        traces.append(go.Scatterpolar(
            r=scores + scores[:1],
            theta=labels + labels[:1],
            customdata=names + names[:1],
            name=name,
            mode="lines+markers",
            line=dict(color=color, width=2, dash=dash),
            marker=dict(size=5),
            fill="toself",
            fillcolor=fill,
            hovertemplate="%{customdata}<br>Cosinus : %{r:.2f}<extra>%{fullData.name}</extra>",
        ))

    return _figure(
        *traces,
        height=310,
        margin=dict(l=45, r=45, t=25, b=12),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.12),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[-1, 1], tickvals=[-1, 0, 0.5, 1], gridcolor=GRID),
            angularaxis=dict(gridcolor=GRID, direction="clockwise", rotation=90),
        ),
    )


def ranking_chart(items: Sequence[dict]) -> go.Figure:
    """Affiche les scores relatifs des cinq premiers vins éligibles."""
    top = items[:5]
    ranks = [str(rank) for rank in range(1, len(top) + 1)]
    return _figure(
        go.Bar(
            x=[100 * round(float(item["score"]), 4) for item in top],
            y=ranks,
            customdata=[escape(item["wine"]["title"]) for item in top],
            orientation="h",
            marker_color=[BORDEAUX if rank == "1" else "#93516b" for rank in ranks],
            texttemplate="%{x:.0f}",
            textposition="auto",
            insidetextfont=dict(color="white"),
            outsidetextfont=dict(color="#1d1d1f"),
            hovertemplate="%{customdata}<br>Score : %{x:.1f} / 100<extra></extra>",
        ),
        height=285,
        margin=dict(l=32, r=18, t=10, b=40),
        bargap=0.36,
        xaxis=dict(range=[0, 100], dtick=25, gridcolor=GRID, fixedrange=True),
        yaxis=dict(type="category", autorange="reversed", fixedrange=True),
    )


def sentence_heatmap(analysis: SentenceAnalysis) -> go.Figure | None:
    """Compare chaque phrase saisie aux cinq blocs sur l'échelle du cosinus."""
    if not analysis.sentences:
        return None

    blocks = load_blocks()
    names = [block["name_fr"] for block in blocks]
    labels = [BLOCK_AXIS[block["id"]] for block in blocks]
    rows = [str(rank) for rank in range(1, len(analysis.sentences) + 1)]
    scores = [
        [float(analysis.block_scores[name][index]) for name in names]
        for index in range(len(rows))
    ]
    # Plotly interprète certains éléments HTML dans ses infobulles.
    labels_and_phrases = [
        [[name, "<br>".join(escape(line) for line in wrap(sentence, width=56))] for name in names]
        for sentence in analysis.sentences
    ]

    return _figure(
        go.Heatmap(
            x=labels,
            y=rows,
            z=scores,
            customdata=labels_and_phrases,
            zmin=-1,
            zmax=1,
            colorscale=[[0, PROFILE_BLUE], [0.5, "#f5f5f7"], [1, BORDEAUX]],
            colorbar=dict(orientation="h", len=0.6, thickness=8, tickvals=[-1, 0, 1],
                          yref="container", y=0.03, yanchor="bottom"),
            xgap=2,
            ygap=2,
            texttemplate="%{z:.2f}",
            hovertemplate="%{customdata[0]}<br>%{customdata[1]}<br>Cosinus : %{z:.2f}<extra></extra>",
        ),
        height=max(190, 101 + 34 * len(rows)),
        margin=dict(l=44, r=10, t=41, b=53),
        xaxis=dict(side="top", fixedrange=True),
        yaxis=dict(type="category", autorange="reversed", fixedrange=True, title="Phrase"),
    )
