import pandas as pd
import plotly.express as px
from faicons import icon_svg as icon
from shinyswatch.theme import minty as shiny_theme

from shiny import render, ui, App

from shinywidgets import render_widget, output_widget


def get_hevy_data():
    PATH_TO_EXPORT = "data/hevy/20250426_HevyExport.csv"
    df = pd.read_csv(PATH_TO_EXPORT, sep=",", encoding="utf-8")
    return df


def clean_hevy_data(df):
    df[["start_time", "end_time"]] = df[["start_time", "end_time"]].apply(
        pd.to_datetime, format="%d %b %Y, %H:%M"
    )
    df["date"] = df["start_time"].dt.date
    df["id_workout"] = df.groupby(
        ["date", "title"]
    ).ngroup()  # Group by workout date and title
    df["id_workout"] = (
        df["id_workout"].astype(str).str.pad(width=3, side="left", fillchar="0")
    )  # Convert to string for unique ID creation

    # Group by workout ID
    dfs = []  # Create an empty list to store processed DataFrames

    df_workouts = []
    for id_workout, workout in df.groupby("id_workout"):
        df_exercises = []
        # Group exercises within each workout and create a unique ID
        ids = workout.groupby("exercise_title").ngroup()  # Group by exercise title
        workout["id_exercise"] = (
            id_workout
            + "_"
            + ids.astype(str).str.pad(width=2, side="left", fillchar="0")
        )  # Create unique exercise ID

        def one_rep_max(weight, reps):
            return weight * (1 + reps / 30)

        for id_exercise, exercise in workout.groupby("id_exercise"):
            exercise["one_rep_max"] = max(
                one_rep_max(exercise["weight_kg"], exercise["reps"])
            )
            exercise["max_weight"] = exercise["weight_kg"].max()
            df_exercises.append(exercise)
        workout = pd.concat(df_exercises).reset_index(
            drop=True
        )  # Concatenate exercises within the workout
        dfs.append(workout)

    df_processed = pd.concat(dfs).reset_index(drop=True)  # Concatenate and reset index

    df_processed["set_index"] += 1  # Increment set_index to start from 1
    df_processed = df_processed[df_processed["reps"].notna()].copy()
    df_processed["reps"] = df_processed["reps"].astype(int)  # Convert reps to integer
    return df_processed


def get_exercise_titles(df_processed):
    return df_processed.value_counts("exercise_title").index.tolist()


df = get_hevy_data()
df_processed = clean_hevy_data(df)
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
    @render.text
    def max_weight_lifted():
        exercise = input.exercise()
        date_range = input.date()
        filters = (
            (df_processed["exercise_title"] == exercise)
            & (df_processed["date"] >= date_range[0])
            & (df_processed["date"] <= date_range[1])
        )
        return f"{df_processed.loc[filters, 'max_weight'].max()} kg"

    @render.text
    def one_rep_max():
        exercise = input.exercise()
        date_range = input.date()
        filters = (
            (df_processed["exercise_title"] == exercise)
            & (df_processed["date"] >= date_range[0])
            & (df_processed["date"] <= date_range[1])
        )
        return f"{df_processed.loc[filters, 'one_rep_max'].max():.1f} kg"

    @render.text
    def total_weight_lifted():
        exercise = input.exercise()
        date_range = input.date()
        filters = (
            (df_processed["exercise_title"] == exercise)
            & (df_processed["date"] >= date_range[0])
            & (df_processed["date"] <= date_range[1])
        )
        df_exercise = df_processed[filters].copy()
        weight_lifted = df_exercise["weight_kg"] * df_exercise["reps"]
        total_weight = weight_lifted.sum()
        return f"{total_weight} kg"

    @render_widget
    def line_plot():
        exercise = input.exercise()
        date_range = input.date()
        df_line = df_processed.copy()
        if exercise:
            df_line = df_line[df_line["exercise_title"] == exercise]
        else:
            return None
        if date_range is not None:
            start_date, end_date = date_range
            df_line = df_line[
                (df_line["date"] >= start_date) & (df_line["date"] <= end_date)
            ]
        metric = input.type_metric_for_exercise()
        return px.line(
            df_line,
            x=df_line["date"].astype(str),
            y=metric,
            title=f"Exercise: {exercise}",
            labels={"x": "Date", "y": metric},
        )

    @render_widget
    def hist():
        exercise = input.exercise()
        date_range = input.date()
        filters = (
            (df_processed["exercise_title"] == exercise)
            & (df_processed["date"] >= date_range[0])
            & (df_processed["date"] <= date_range[1])
        )
        df_hist = df_processed.loc[filters, ["id_exercise", "reps"]].copy()
        return px.histogram(
            df_hist,
            x="reps",
            title=f"Exercise: {exercise}",
            labels={"x": "Reps"},
            color_discrete_sequence=["#636EFA"],
        )

    @render.data_frame
    def data_table():
        exercise = input.exercise()
        date_range = input.date()
        if exercise is None:
            return None
        filtered_df = df[
            (df["exercise_title"] == exercise)
            & (df["date"] >= date_range[0])
            & (df["date"] <= date_range[1])
        ].copy()
        return filtered_df[["title", "date", "reps", "weight_kg", "set_index"]].copy()


app = App(app_ui, server)
