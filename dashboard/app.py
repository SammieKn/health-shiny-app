import pandas as pd
import plotly.express as px
from faicons import icon_svg as icon
from shinyswatch.theme import minty as shiny_theme
from dashboard.processing.data_processing import get_hevy_data

from shiny import render, ui, App, reactive

from shinywidgets import render_widget, output_widget

def get_exercise_titles(df_processed):
    return df_processed.value_counts("exercise_title").index.tolist()


df_processed = get_hevy_data()
exercise_titles = get_exercise_titles(df_processed)


def ui_hevy():
    # Placeholder for UI logic
    sidebar = ui.sidebar(
        ui.input_select("exercise", "Exercise", get_exercise_titles(df_processed)),
        ui.input_date_range(
            "date",
            "Date range",
            start=df_processed["date"].min(),
            end=df_processed["date"].max(),
            format="dd-mm-yy",
        ),
        ui.input_selectize(
            "type_metric_for_exercise",
            "Select a metric",
            {"one_rep_max": "One Rep Max", "max_weight": "Max Weight"},
            selected="max_weight",
        ),
    )

    kpis = ui.layout_columns(
        ui.value_box(
            title="Max Weight lifted",
            showcase=icon("dumbbell"),
            value=ui.output_text("max_weight_lifted"),
        ),
        ui.value_box(
            title="One Rep Max",
            showcase=icon("medal"),
            value=ui.output_text("one_rep_max"),
        ),
        ui.value_box(
            title="Total Weight Lifted",
            showcase=icon("weight-hanging"),
            value=ui.output_text("total_weight_lifted"),
        ),
        fill=True,
    )

    plots = ui.card(
        ui.layout_columns(
            output_widget("line_plot"),
            output_widget("hist"),
            col_widths=(8, 4),
        )
    )
    table = ui.card(
        ui.output_data_frame("data_table"),
    )

    return ui.page_sidebar(sidebar, kpis, plots, table, fillable=True)


app_ui = ui.page_navbar(
    ui.nav_panel("Summary", "Content For Summary", icon=icon("address-card")),
    ui.nav_panel("Weight Lifting", ui_hevy(), icon=icon("dumbbell")),
    ui.nav_panel("Cardio", "Content For Cardio", icon=icon("person-running")),
    ui.nav_panel("Health", "Content For Health", icon=icon("apple")),
    title="Personal health dashboard",
    id="page",
    theme=shiny_theme,
)


def server(input, output, session):
    # Placeholder for server logic
    @reactive.calc
    def filter_df():
        exercise = input.exercise()
        date_range = input.date()

        filter_exercise = True
        filter_date = True

        if exercise:
            filter_exercise = df_processed["exercise_title"] == exercise
        if date_range:
            start_date, end_date = date_range
            filter_date = (df_processed["date"] >= start_date) & (
                df_processed["date"] <= end_date
            )
        if exercise or date_range:
            filters = filter_exercise & filter_date
            return df_processed[filters].copy()
        return df_processed.copy()

    @render.text
    def max_weight_lifted():
        df = filter_df()
        return f"{df['max_weight'].max()} kg"

    @render.text
    def one_rep_max():
        df = filter_df()
        return f"{df['one_rep_max'].max():.1f} kg"

    @render.text
    def total_weight_lifted():
        df_exercise = filter_df()
        weight_lifted = df_exercise["weight_kg"] * df_exercise["reps"]
        total_weight = weight_lifted.sum()
        return f"{total_weight} kg"

    @render_widget
    def line_plot():
        df_line = filter_df()
        metric = input.type_metric_for_exercise()
        return px.line(
            df_line,
            x=df_line["date"].astype(str),
            y=metric,
            title=f"Exercise: {input.exercise()}",
            labels={"x": "Date", "y": metric},
        )

    @render_widget
    def hist():
        df_hist = filter_df()
        return px.histogram(
            df_hist,
            x="reps",
            title=f"Exercise: {input.exercise()}",
            labels={"x": "Reps"},
            color_discrete_sequence=["#636EFA"],
        )

    @render.data_frame
    def data_table():
        filtered_df = filter_df()
        return filtered_df[["title", "date", "reps", "weight_kg", "set_index"]].copy()


app = App(app_ui, server)
