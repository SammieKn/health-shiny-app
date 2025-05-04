import pandas as pd
import plotly.express as px
from faicons import icon_svg as icon

from shiny.express import input, render, ui
from shinywidgets import render_plotly

PATH_TO_EXPORT = "data/hevy/20250426_HevyExport.csv"

df = pd.read_csv(PATH_TO_EXPORT, sep=",", encoding="utf-8")
df[["start_time", "end_time"]] = df[["start_time", "end_time"]].apply(pd.to_datetime, format="%d %b %Y, %H:%M")
df["date"] = df["start_time"].dt.date
df["id_workout"] = df.groupby(["date", "title"]).ngroup()  # Group by workout date and title
df["id_workout"] = df["id_workout"].astype(str).str.pad(width=3, side="left", fillchar="0")  # Convert to string for unique ID creation

# Group by workout ID
dfs = []  # Create an empty list to store processed DataFrames

df_workouts = []
for id_workout, workout in df.groupby("id_workout"):
    df_exercises = []
    # Group exercises within each workout and create a unique ID
    ids = workout.groupby("exercise_title").ngroup()  # Group by exercise title
    workout["id_exercise"] = id_workout + "_" + ids.astype(str).str.pad(width=2, side="left", fillchar="0")  # Create unique exercise ID
    def one_rep_max(weight, reps):
        return weight * (1 + reps / 30) 
    for id_exercise, exercise in workout.groupby("id_exercise"):
        exercise["one_rep_max"] = max(one_rep_max(exercise["weight_kg"], exercise["reps"]))
        exercise["max_weight"] = exercise["weight_kg"].max()
        df_exercises.append(exercise)
    workout = pd.concat(df_exercises).reset_index(drop=True)  # Concatenate exercises within the workout
    dfs.append(workout)

df_processed = pd.concat(dfs).reset_index(drop=True)  # Concatenate and reset index

df_processed["set_index"] += 1  # Increment set_index to start from 1
df_processed = df_processed[df_processed["reps"].notna()].copy()
df_processed["reps"] = df_processed["reps"].astype(int)  # Convert reps to integer

exercise_titles = df_processed.value_counts("exercise_title").index.tolist()

ui.page_opts(
    title="Personal health data",
    fill_screen=True,
)
with ui.sidebar():
    ui.input_select("exercise", "Exercise", exercise_titles)
    ui.input_date_range("date", "Date range", start=df["date"].min(),  end=df["date"].max(), format="dd-mm-yy")
    ui.input_selectize(
        "type_metric_for_exercise",
        "Select a metric",
        {"one_rep_max": "One Rep Max", "max_weight": "Max Weight"},
        selected="max_weight",
    )

with ui.layout_columns(fill=True):
    with ui.value_box(showcase=icon("dumbbell")):
        "Max Weight lifted"
        @render.ui
        def max_weight_lifted():
            exercise = input.exercise()
            date_range = input.date()
            filters = (df_processed["exercise_title"] == exercise) & (df_processed["date"] >= date_range[0]) & (df_processed["date"] <= date_range[1])
            return f"{df_processed.loc[filters, 'max_weight'].max()} kg"
    with ui.value_box(showcase=icon("medal")):
        "One Rep Max"
        @render.ui
        def _():
            exercise = input.exercise()
            date_range = input.date()
            filters = (df_processed["exercise_title"] == exercise) & (df_processed["date"] >= date_range[0]) & (df_processed["date"] <= date_range[1])
            return f"{df_processed.loc[filters, 'one_rep_max'].max():.1f} kg"

    with ui.value_box(showcase=icon("weight-hanging")):
        "Total Weight Lifted"
        @render.ui
        def total_weight_lifted():
            exercise = input.exercise()
            date_range = input.date()
            filters = (df_processed["exercise_title"] == exercise) & (df_processed["date"] >= date_range[0]) & (df_processed["date"] <= date_range[1])
            df_exercise = df_processed[filters].copy()
            weight_lifted = df_exercise["weight_kg"] * df_exercise["reps"]
            total_weight = weight_lifted.sum()
            return f"{total_weight} kg"

with ui.card(full_screen=True, class_="my-3"):
    with ui.layout_columns(col_widths=(8, 4)):
        @render_plotly
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
                df_line = df_line[(df_line["date"] >= start_date) & (df_line["date"] <= end_date)]
            metric = input.type_metric_for_exercise()
            return px.line(
                df_line,
                x=df_line["date"].astype(str),
                y=metric,
                title=f"Exercise: {exercise}",
                labels={"x": "Date", "y": metric},
                )

        @render_plotly
        def hist():
            exercise = input.exercise()
            date_range = input.date()
            filters = (df_processed["exercise_title"] == exercise) & (df_processed["date"] >= date_range[0]) & (df_processed["date"] <= date_range[1])
            df_hist = df_processed.loc[filters, ["id_exercise", "reps"]].copy()
            return px.histogram(df_hist, x="reps", title=f"Exercise: {exercise}", labels={"x": "Reps"}, color_discrete_sequence=["#636EFA"])

with ui.card(full_screen=True):
    ui.card_header("Exercise data")
    @render.data_frame
    def data_table():
        exercise = input.exercise()
        date_range = input.date()
        if exercise is None:
            return None
        filtered_df = df[(df["exercise_title"] == exercise) & (df["date"] >= date_range[0]) & (df["date"] <= date_range[1])].copy()
        return filtered_df[["title", "date", "reps", "weight_kg", "set_index"]].copy()
