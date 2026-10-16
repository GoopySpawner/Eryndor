# Eryndor Encounter Generator

## Host the web app on your local network

1. Open PowerShell in this folder and run:

   ```powershell
   py web_app.py
   ```

2. Set and confirm the DM password, then set a different party-page password.
3. Open one of the printed `http://<address>:8000` links on this PC or another
   device connected to the same local network. The browser will ask for the
   DM password on the encounter-generator page; use `eryndor` as the username.
   Share the same address with `/party` appended and give the party only the
   party-page password. The party page provides the shared calendar, notes, and
   inventory; it does not expose encounter tools or DM history.
4. Keep the PowerShell window open while using the app. Press **Ctrl+C** there
   to stop the server.

Encounter history and campaign calendar are shared by all connected devices
and saved together in the root-level `Saved-Data/` directory. Encounter history
is stored in `Saved-Data/encounter_history.json`; calendar state is stored in
`Saved-Data/campaign_calendar.json`; party notes and inventory are stored in
`Saved-Data/party_data.json`. The party calendar is view-only. The calendar's
initial date is randomly selected from April through June of Year 1, then kept
across restarts.

The `/party` page links to `/bastion`, a shared Bastion tracker accessible with
the party-page password. Party credentials can view and edit all Bastion state,
including resources, facilities, turns, and event resolutions. Bastion state is
stored in `Bastion Information/bastion_state.json`, separate from party data.
The configured test Bastion has a Garden, Armory, Barracks, and Storehouse
in four Roomy slots, a Residuum Crucible in its Vast slot, and six Cramped
facilities (Walls, Watchtower, Shrine, Veil Gauge Resonance Chamber, Lamp Lines,
and Triage Tent). The tracker supports facility assignments and damage,
resource editing, Veil Expansion, guided weekly turns,
production and defense rolls, and facility/event reference information.
Facility gold costs (500 gp Cramped, 1,000 gp Roomy, 3,000 gp Vast) are reminders
only and are not deducted. Resource capacity is checked at the start of each
Bastion Turn; operational Roomy producers provide 10 storage, Vast producers 25,
and matching Cramped storage facilities add 5. Excess is removed at Upkeep
rather than blocking production during the current turn. Gold has no facility
storage cap.

Combat-table results are always rolled randomly and are not tracked or exhausted
by encounter history.
Every combat rolls one initiative d20 per enemy and lists the results from
highest to lowest, showing both the color and creature type. The first twelve
enemies use red, orange, yellow, green, blue, purple, pink, black, grey, brown,
magenta, and white labels; additional enemies are identified by numbered
singular monster names. Reinforcements receive a separate initiative list.
This also applies to biome combats and rest ambushes.
Reinforcement group sizes show their `1d4` expression and individual die
result alongside the total.
Each Hollow in combat also rolls 3d6 for its DR; totals of 3-7 yield no
residuum, 8-13 yield 1 residuum, and 14-18 yield 2 residuum.

Each generated encounter advances the clock by one six-hour segment. The four
daily segments are 10:01 PM-4:00 AM, 4:01 AM-10:00 AM, 10:01 AM-4:00 PM, and
4:01 PM-10:00 PM. Use **Advance 1 Segment** or **Back 1 Segment** to move time
without generating an encounter. **Long Rest** rolls the last shelter die three
times. Each 1 triggers a separate Combat-table ambush and is recorded as an
encounter. If interrupted one or more times, the long rest extends from three
to four days total; the number of interruptions does not add further delay.
Otherwise, the long rest advances three days. Both outcomes preserve the time
segment.
**Short Rest** rolls the shelter die from the last generated encounter. A 1
triggers a Combat-table ambush, records that combat encounter, and advances two
segments total; any other result completes the rest and advances one segment.
The calendar uses
seven-day Monday-to-Sunday weeks and 28-day months; Undecimber follows December.
The calendar highlights **Resolve Bastion Turn** on Mondays at segment 2/4 and
prompts before generating an encounter then. If a long rest passes a Monday's
Bastion Turn, it asks whether the turn has been resolved. On the 26th of each
month at segment 1/4, it displays **FULL MOON DID THEY PREPARE?**
Resetting encounter history does not reset the calendar. The existing Tkinter
app can still be started with `py main.py`. Calendar rules and persistence are
implemented in the root-level `calendar.py`.

The web server uses HTTP, not HTTPS. Use it only on a trusted private network,
do not forward its port from your router, and do not use the password on an
untrusted or public Wi-Fi network. If Windows Firewall asks, allow access only
on private networks.

To use another port, run `py web_app.py --port 8765` and use the address printed
by the server.
