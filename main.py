import importlib.util
from pathlib import Path


encounters_path = Path(__file__).parent / "Hex-Encounters" / "encounters.py"
encounters_spec = importlib.util.spec_from_file_location("eryndor_encounters", encounters_path)
if encounters_spec is None or encounters_spec.loader is None:
    raise ImportError(f"Unable to load encounter roller from {encounters_path}")

encounters = importlib.util.module_from_spec(encounters_spec)
encounters_spec.loader.exec_module(encounters)


def main():
    import tkinter as tk
    from tkinter import messagebox
    from tkinter.scrolledtext import ScrolledText
    from tkinter.ttk import Combobox

    window = tk.Tk()
    window.title("Eryndor")
    window.geometry("760x560")
    current_biome = tk.StringVar(value="Woodlands")

    try:
        seen_encounters, excluded_tables = encounters.load_history()
    except (OSError, ValueError) as error:
        messagebox.showerror(
            "Unable to Load Encounter History",
            f"Encounter history could not be loaded:\n{error}",
            parent=window,
        )
        window.destroy()
        return

    try:
        last_rest_die = encounters.load_last_rest_die()
    except (OSError, ValueError) as error:
        messagebox.showerror(
            "Unable to Load Last Encounter",
            f"The last encounter's rest die could not be loaded:\n{error}",
            parent=window,
        )
        window.destroy()
        return

    try:
        calendar_status = encounters.campaign_calendar.get_calendar_display(
            encounters.campaign_calendar.load_calendar()
        )
    except (OSError, ValueError) as error:
        messagebox.showerror(
            "Unable to Load Campaign Calendar",
            f"The campaign calendar could not be loaded:\n{error}",
            parent=window,
        )
        window.destroy()
        return

    biome_frame = tk.Frame(window)
    biome_frame.pack(padx=20, pady=(15, 5))

    biome_label = tk.Label(biome_frame, text="Current biome:")
    biome_label.pack(side=tk.LEFT, padx=(0, 10))

    def on_biome_selected(_event=None):
        update_history_label()

    biome_selector = Combobox(
        biome_frame,
        textvariable=current_biome,
        values=encounters.BIOMES,
        state="readonly",
    )
    biome_selector.pack(side=tk.LEFT)
    biome_selector.bind("<<ComboboxSelected>>", on_biome_selected)

    result_label = tk.Label(window, text="Click the button to generate an encounter.")
    result_label.pack(padx=20, pady=(20, 10))

    history_label = tk.Label(window)
    history_label.pack(padx=20, pady=(0, 10))

    calendar_label = tk.Label(window, font=("Consolas", 9), justify=tk.CENTER)
    calendar_label.pack(padx=20, pady=(0, 10))

    rest_status_label = tk.Label(
        window,
        font=("Segoe UI", 16, "bold"),
        relief=tk.RIDGE,
        borderwidth=2,
        padx=16,
        pady=6,
    )
    full_moon_label = tk.Label(
        window,
        text="FULL MOON DID THEY PREPARE?",
        font=("Segoe UI", 16, "bold"),
        foreground="#30234c",
        background="#e1d4ff",
        relief=tk.RIDGE,
        borderwidth=2,
        padx=16,
        pady=6,
    )

    rest_location_label = tk.Label(window, text="Rest location is rolled per encounter.")
    rest_location_label.pack(padx=20, pady=(0, 10))

    controls_frame = tk.Frame(window)
    controls_frame.pack(padx=20, pady=(0, 10))

    result_text = ScrolledText(window, wrap=tk.WORD, width=80, height=20)
    result_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    result_text.insert(tk.END, "Your encounter will appear here.")
    result_text.config(state=tk.DISABLED)

    def update_calendar_label(status):
        month_grid = ["Mo Tu We Th Fr Sa Su"]
        for week in range(4):
            days = []
            for weekday in range(7):
                day = week * 7 + weekday + 1
                days.append(
                    f"*{day:02d}" if day == status["day"] else f" {day:02d}"
                )
            month_grid.append(" ".join(days))
        calendar_label.config(
            text=(
                f"Campaign date: {status['weekday']}, {status['dateLabel']}\n"
                f"{status['segmentName']}  |  {status['timeSlot']}\n"
                + "\n".join(month_grid)
            )
        )
        rest_status = {
            1: ("Time to Rest", "#7a1f1f", "#ffe0d6"),
            2: (
                ("Resolve Bastion Turn", "#30234c", "#e1d4ff")
                if status["weekday"] == "Monday"
                else None
            ),
            4: ("Prepare for Rest", "#70400b", "#ffedc2"),
        }.get(status["segment"])
        if rest_status is None:
            rest_status_label.pack_forget()
        else:
            text, foreground, background = rest_status
            rest_status_label.config(
                text=text,
                foreground=foreground,
                background=background,
            )
            rest_status_label.pack(
                before=rest_location_label,
                padx=20,
                pady=(0, 10),
            )
        if status["day"] == 26 and status["segment"] == 1:
            full_moon_label.pack(
                before=rest_location_label,
                padx=20,
                pady=(0, 10),
            )
        else:
            full_moon_label.pack_forget()

    update_calendar_label(calendar_status)

    def update_history_label(table_name=None):
        if table_name is None:
            available_tables = encounters.get_encounter_tables_in_pool(
                current_biome.get()
            )
            history_label.config(
                text=(
                    f"Encounter tables available: "
                    f"{len(available_tables - excluded_tables)} "
                    f"of {len(available_tables)}"
                )
            )
        elif table_name in seen_encounters:
            history_label.config(
                text=(
                    f"{table_name}: {len(seen_encounters[table_name])}/"
                    f"{len(encounters.TABLES[table_name])} "
                    "unique encounters have appeared"
                )
            )
        else:
            history_label.config(
                text=(
                    "No encounter table is available for "
                    f"{current_biome.get()}."
                )
            )

    update_history_label()

    def acknowledge_exhausted_table(table_name):
        dialog = tk.Toplevel(window)
        dialog.title("Encounter Table Exhausted")
        dialog.transient(window)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        message = (
            f"All {len(encounters.TABLES[table_name])} {table_name} encounters "
            "have appeared. This table "
            "will be removed from the pool and the dice will be rolled again."
        )
        tk.Label(dialog, text=message, wraplength=360, padx=20, pady=20).pack()
        tk.Button(
            dialog,
            text="I Understand",
            command=dialog.destroy,
        ).pack(pady=(0, 20))
        dialog.wait_window()

    def generate_encounter():
        nonlocal seen_encounters, excluded_tables, calendar_status, last_rest_die

        if calendar_status["segment"] == 4 and not messagebox.askyesno(
            "Travel During Rest?",
            "The party should start a short rest. Generating an encounter "
            "means they are traveling through their rest and will have to "
            "roll exhaustion. Is this what they want?",
            parent=window,
        ):
            return
        if (
            calendar_status["segment"] == 2
            and calendar_status["weekday"] == "Monday"
            and not messagebox.askyesno(
                "Bastion Turn",
                "A bastion turn should have occurred. Have you resolved "
                "a bastion turn?",
                parent=window,
            )
        ):
            return

        while True:
            available_tables = encounters.get_encounter_tables_in_pool(
                current_biome.get()
            )
            if available_tables <= excluded_tables:
                messagebox.showinfo(
                    "All Encounter Tables Exhausted",
                    f"All encounter tables for {current_biome.get()} are "
                    "exhausted. Reset encounter history or choose another "
                    "biome to continue.",
                    parent=window,
                )
                return

            rolled_d20, rolled_d6 = encounters.roll_dice(
                excluded_tables,
                current_biome.get(),
            )
            table_name, outcome = encounters.get_encounter(
                rolled_d20,
                rolled_d6,
                current_biome.get(),
            )
            if table_name not in encounters.TABLES:
                d20 = rolled_d20
                break

            if table_name == "Combat":
                d20 = rolled_d20
                outcome = encounters.TABLES[table_name][d20]
                break

            d20 = encounters.next_unseen_result(
                table_name,
                rolled_d20,
                seen_encounters,
            )
            if d20 is None:
                acknowledge_exhausted_table(table_name)
                updated_excluded_tables = set(excluded_tables)
                updated_excluded_tables.add(table_name)
                try:
                    encounters.save_history(
                        seen_encounters,
                        updated_excluded_tables,
                    )
                except OSError as error:
                    messagebox.showerror(
                        "Unable to Save Encounter History",
                        f"The exhausted table could not be removed:\n{error}",
                        parent=window,
                    )
                    return
                excluded_tables = updated_excluded_tables
                update_history_label()
                continue

            outcome = encounters.TABLES[table_name][d20]
            if table_name != "Combat":
                updated_seen_encounters = {
                    name: set(results)
                    for name, results in seen_encounters.items()
                }
                updated_seen_encounters[table_name].add(d20)
                try:
                    encounters.save_history(
                        updated_seen_encounters,
                        excluded_tables,
                    )
                except OSError as error:
                    messagebox.showerror(
                        "Unable to Save Encounter History",
                        f"The encounter was not recorded:\n{error}",
                        parent=window,
                    )
                    return
                seen_encounters = updated_seen_encounters
            break

        rest_location, shelter_die = encounters.roll_rest_location()
        last_rest_die = int(shelter_die[1:])
        try:
            encounters.save_last_rest_die(last_rest_die)
        except OSError as error:
            messagebox.showerror(
                "Unable to Save Last Encounter",
                f"The encounter was generated, but its rest die could not "
                f"be saved:\n{error}",
                parent=window,
            )
            return
        short_rest_button.config(state=tk.NORMAL)
        long_rest_button.config(state=tk.NORMAL)
        luxury_goods = encounters.roll_luxury_goods_reward(table_name, d20)
        if luxury_goods is not None:
            outcome += f"\n\n{luxury_goods}"

        if encounters.is_combat_encounter(table_name, d20):
            outcome = encounters.format_combat_encounter(
                table_name,
                d20,
                current_biome.get(),
                outcome,
            )
        try:
            calendar_status = (
                encounters.campaign_calendar.record_calendar_encounter()
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Unable to Save Campaign Calendar",
                f"The encounter was generated, but campaign time could not "
                f"be saved:\n{error}",
                parent=window,
            )
        else:
            update_calendar_label(calendar_status)

        result_label.config(
            text=(
                (
                    f"D100: {d20}"
                    if table_name == "Environmental Vignettes"
                    else (
                        f"D20: {rolled_d20}"
                        + (f" -> {d20}" if rolled_d20 != d20 else "")
                    )
                )
                + f"    D6: {rolled_d6}    Table: {table_name}"
            )
        )
        update_history_label(table_name)
        rest_location_label.config(
            text=f"Random rest location: {rest_location} ({shelter_die})"
        )
        result_text.config(state=tk.NORMAL)
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, outcome)
        result_text.config(state=tk.DISABLED)

    generate_button = tk.Button(
        controls_frame,
        text="Generate Encounter",
        command=generate_encounter,
    )
    generate_button.pack(side=tk.LEFT, padx=5)

    def short_rest():
        nonlocal seen_encounters, excluded_tables, calendar_status
        if last_rest_die is None:
            messagebox.showinfo(
                "No Rest Location",
                "Generate an encounter before taking a short rest.",
                parent=window,
            )
            return

        shelter_roll = encounters.random.randint(1, last_rest_die)
        try:
            if shelter_roll == 1:
                (
                    rolled_d20,
                    combat_result,
                    outcome,
                    repeated_result,
                    updated_seen_encounters,
                    updated_excluded_tables,
                ) = encounters.generate_ambush_encounter(current_biome.get())
                calendar_status = (
                    encounters.campaign_calendar.record_calendar_encounter()
                )
                calendar_status = (
                    encounters.campaign_calendar.adjust_calendar_segment(1)
                )
                seen_encounters = updated_seen_encounters
                excluded_tables = updated_excluded_tables
                update_history_label("Combat")
                result_label.config(
                    text=(
                        f"Short Rest ambush (D{last_rest_die}: 1)  |  "
                        f"Combat D20: {combat_result}"
                        + (
                            f" (rolled {rolled_d20})"
                            if rolled_d20 != combat_result
                            else ""
                        )
                    )
                )
                rest_location_label.config(
                    text="The party was attacked during their short rest."
                )
                if repeated_result:
                    outcome += (
                        "\n\nAll Combat table entries have appeared; "
                        "a previously seen result was repeated."
                    )
            else:
                calendar_status = (
                    encounters.campaign_calendar.adjust_calendar_segment(1)
                )
                outcome = (
                    f"Short rest completed without interruption "
                    f"(shelter check D{last_rest_die}: {shelter_roll})."
                )
                result_label.config(
                    text=f"Short Rest (D{last_rest_die}: {shelter_roll})"
                )
                rest_location_label.config(text="Short rest completed.")

            update_calendar_label(calendar_status)
            result_text.config(state=tk.NORMAL)
            result_text.delete("1.0", tk.END)
            result_text.insert(tk.END, outcome)
            result_text.config(state=tk.DISABLED)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Unable to Complete Short Rest",
                f"The short rest could not be recorded:\n{error}",
                parent=window,
            )

    short_rest_button = tk.Button(
        controls_frame,
        text="Short Rest",
        command=short_rest,
        state=tk.NORMAL if last_rest_die is not None else tk.DISABLED,
    )

    def adjust_time(direction):
        nonlocal calendar_status
        try:
            calendar_status = (
                encounters.campaign_calendar.adjust_calendar_segment(direction)
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Unable to Update Campaign Time",
                f"Campaign time could not be updated:\n{error}",
                parent=window,
            )
            return
        update_calendar_label(calendar_status)

    back_time_button = tk.Button(
        controls_frame,
        text="Back 1 Segment",
        command=lambda: adjust_time(-1),
    )
    back_time_button.pack(side=tk.LEFT, padx=5)

    advance_time_button = tk.Button(
        controls_frame,
        text="Advance 1 Segment",
        command=lambda: adjust_time(1),
    )
    advance_time_button.pack(side=tk.LEFT, padx=5)
    short_rest_button.pack(side=tk.LEFT, padx=5)

    def long_rest_crosses_bastion_turn(status, days_advanced):
        weekday_index = encounters.campaign_calendar.CALENDAR_WEEKDAYS.index(
            status["weekday"]
        )
        for day_offset in range(days_advanced + 1):
            if (
                weekday_index + day_offset
            ) % len(encounters.campaign_calendar.CALENDAR_WEEKDAYS) != 0:
                continue
            if day_offset > 0 or status["segment"] <= 2:
                return True
        return False

    def take_long_rest():
        nonlocal seen_encounters, excluded_tables, calendar_status
        if last_rest_die is None:
            messagebox.showinfo(
                "No Rest Location",
                "Generate an encounter before taking a long rest.",
                parent=window,
            )
            return

        start_calendar = calendar_status
        shelter_rolls = [
            encounters.random.randint(1, last_rest_die) for _ in range(3)
        ]
        ambush_count = shelter_rolls.count(1)
        interrupted = ambush_count > 0
        try:
            combat_outcomes = []
            if interrupted:
                for ambush_number in range(ambush_count):
                    (
                        rolled_d20,
                        combat_result,
                        combat_outcome,
                        repeated_result,
                        seen_encounters,
                        excluded_tables,
                    ) = encounters.generate_ambush_encounter(current_biome.get())
                    encounters.campaign_calendar.record_encounter_count()
                    combat_heading = (
                        f"Ambush {ambush_number + 1} - Combat D20: "
                        f"{combat_result}"
                        + (
                            f" (rolled {rolled_d20})"
                            if rolled_d20 != combat_result
                            else ""
                        )
                    )
                    if repeated_result:
                        combat_outcome += (
                            "\n\nAll Combat table entries have appeared; "
                            "a previously seen result was repeated."
                        )
                    combat_outcomes.append(
                        f"{combat_heading}\n\n{combat_outcome}"
                    )
                outcome = (
                    f"Long rest interrupted {ambush_count} time(s). "
                    "The rest is extended by one day total.\n\n"
                    + "\n\n".join(combat_outcomes)
                )
            else:
                outcome = "Long rest completed without interruption."
            days_advanced = 4 if interrupted else 3
            calendar_status = (
                encounters.campaign_calendar.take_long_rest(
                    days=days_advanced
                )
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Unable to Record Long Rest",
                f"The long rest could not be recorded:\n{error}",
                parent=window,
            )
            return
        update_calendar_label(calendar_status)
        update_history_label("Combat" if interrupted else None)
        result_label.config(
            text=(
                f"Long Rest (D{last_rest_die}: "
                f"{', '.join(str(roll) for roll in shelter_rolls)})"
            )
        )
        rest_location_label.config(
            text=(
                "Long rest interrupted; extended to 4 days."
                if interrupted
                else "Long rest completed; advanced 3 days."
            )
        )
        result_text.config(state=tk.NORMAL)
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, outcome)
        result_text.config(state=tk.DISABLED)
        if long_rest_crosses_bastion_turn(start_calendar, days_advanced):
            messagebox.askyesno(
                "Bastion Turn",
                "A Bastion Turn should have occurred during the long rest. "
                "Have you resolved a Bastion Turn?",
                parent=window,
            )

    long_rest_button = tk.Button(
        controls_frame,
        text="Long Rest",
        command=take_long_rest,
        state=tk.NORMAL if last_rest_die is not None else tk.DISABLED,
    )
    long_rest_button.pack(side=tk.LEFT, padx=5)

    def reset_history():
        nonlocal seen_encounters, excluded_tables
        if not messagebox.askyesno(
            "Reset Encounter History",
            "Clear all seen encounters and restore every table to the pool?",
            parent=window,
        ):
            return

        empty_seen, empty_excluded = encounters.empty_history()
        try:
            encounters.save_history(empty_seen, empty_excluded)
        except OSError as error:
            messagebox.showerror(
                "Unable to Reset Encounter History",
                f"Encounter history could not be reset:\n{error}",
                parent=window,
            )
            return

        seen_encounters = empty_seen
        excluded_tables = empty_excluded
        update_history_label()
        result_label.config(text="Encounter history reset.")
        rest_location_label.config(text="Rest location is rolled per encounter.")
        result_text.config(state=tk.NORMAL)
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, "Your encounter will appear here.")
        result_text.config(state=tk.DISABLED)

    reset_button = tk.Button(
        controls_frame,
        text="Reset Encounter History",
        command=reset_history,
    )
    reset_button.pack(side=tk.LEFT, padx=5)

    window.mainloop()

if __name__ == "__main__":
    main()
