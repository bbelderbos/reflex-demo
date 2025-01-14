from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, DateTime, func, and_
from sqlmodel import Field
import reflex as rx

WEEKLY_GOAL = 5


class Workout(rx.Model, table=True):
    """Database model for a workout."""

    completed: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class State(rx.State):
    workouts: list[str] = []
    target: int = WEEKLY_GOAL
    current_week_offset: int = 0

    def load_workouts(self, week_offset: int = 0):
        today = datetime.now(timezone.utc)
        start_of_week = datetime(today.year, today.month, today.day) - timedelta(
            days=today.weekday()
        )
        start_of_week += timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=7)

        with rx.session() as session:
            db_workouts = (
                session.query(Workout)
                .filter(
                    and_(
                        Workout.completed >= start_of_week,
                        Workout.completed < end_of_week,
                    )
                )
                .all()
            )
            self.workouts = [
                workout.completed.strftime("%Y-%m-%d %H:%M") for workout in db_workouts
            ]

    @rx.var
    def progress(self) -> int:
        return len(self.workouts)

    @rx.var
    def progress_percentage(self) -> int:
        return int(self.progress / self.target * 100)

    @rx.var
    def goal_reached(self) -> bool:
        return self.progress >= self.target

    @rx.var
    def current_week(self) -> bool:
        return self.current_week_offset == 0

    @rx.var
    def yymm(self) -> str:
        dt = datetime.now(timezone.utc) + timedelta(weeks=self.current_week_offset)
        cal = dt.isocalendar()
        return f"{cal.year} - week {cal.week:02}"

    def load_current_week(self):
        self.load_workouts(self.current_week_offset)

    def show_previous_week(self):
        self.current_week_offset -= 1
        self.load_workouts(self.current_week_offset)

    def show_next_week(self):
        self.current_week_offset += 1
        self.load_workouts(self.current_week_offset)

    def log_workout(self):
        with rx.session() as session:
            workout = Workout()
            session.add(workout)
            session.commit()
        self.load_workouts(self.current_week_offset)


def progress_display() -> rx.Component:
    return rx.vstack(
        rx.text(f"Workouts Completed {State.yymm}:", size="4"),
        rx.progress(value=State.progress_percentage),
    )


def week_navigation_buttons() -> rx.Component:
    return rx.hstack(
        rx.button("Previous Week", on_click=State.show_previous_week, size="2"),
        rx.button("Next Week", on_click=State.show_next_week, size="2"),
        spacing="4",
    )


def conditional_workout_logging_button() -> rx.Component:
    return rx.cond(
        State.goal_reached,
        rx.text("Congrats, you hit your weekly goal 💪 🎉", size="4", color="green"),
        rx.cond(
            State.current_week,
            rx.button(
                "Log Workout",
                on_click=State.log_workout,
                size="4",
                background_color="green",
                color="white",
            ),
            rx.text("", size="4"),
        ),
    )


def workout_list() -> rx.Component:
    return rx.vstack(
        rx.foreach(
            State.workouts,
            lambda workout_date: rx.text(f"Workout done: {workout_date}"),
        ),
    )


def index() -> rx.Component:
    return rx.vstack(
        rx.heading("Fitness Tracker", size="9"),
        progress_display(),
        rx.heading("Workout History", size="7"),
        week_navigation_buttons(),
        rx.input(placeholder="Set goal", on_blur=State.set_target, size="3"),
        workout_list(),
        conditional_workout_logging_button(),
        align="center",
        spacing="4",
    )


app = rx.App()

app.add_page(
    index,
    title="Fitness Tracker",
    on_load=State.load_current_week,
)
