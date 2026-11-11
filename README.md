# Workstation Monitor

A native, read-only Ubuntu task manager for app usage and live CPU, memory, NVIDIA GPU, storage, temperature, and network activity.

Measurements stay in memory on your computer. The app needs no account, cloud service, root daemon, or network listener. This first release does not end processes, change startup programs, record sessions, or measure per-app network bandwidth.

## Get started

The tested baseline is Ubuntu 24.04 with Python 3.12, GTK 4.14, libadwaita 1.5, PyGObject 3.48, and psutil 5.9. Run the app from a graphical desktop session.

Install the native prerequisites on a new Ubuntu installation:

```sh
sudo apt install python3-venv python3-gi python3-gi-cairo python3-cairo \
  gir1.2-gtk-4.0 gir1.2-adw-1 python3-psutil
```

Then clone, prepare the project-local environment, and launch:

```sh
git clone https://github.com/RoryGlenn/workstation-monitor.git
cd workstation-monitor
sh scripts/setup.sh
./run.sh
```

Setup downloads the pinned NVIDIA Python binding. If necessary, it extracts Ubuntu's Cairo/GI bridge into the project. It does not replace system Python. Setup needs internet access for public packages; runtime monitoring works offline. NVIDIA hardware and driver support are optional, and other views continue when GPU measurements are unavailable.

**Overview** opens with a wide CPU timeline, compact memory/GPU/storage panels, temperatures, network receive/send activity, and three busy app rows. New installations use the graphite-and-mint Dark appearance; Settings also offers Light and System. CPU and transfer rates show **Measuring…** until two samples arrive. Select a resource for details, choose **View all apps**, or open **Processes** and search by name or PID.

## Install the desktop launcher

From the project folder:

```sh
.venv/bin/python scripts/install_launcher.py
```

Open **Workstation Monitor** from your desktop's applications menu. The launcher points to this checkout; rerun the installer after moving it. Closing the window stops collection. Automatic startup is not enabled.

The launcher uses Cairo and disables unused OpenGL/Vulkan backends for this app to reduce graphics-driver allocations. GPU monitoring still uses NVIDIA's monitoring API. To compare another renderer, run `GSK_RENDERER=gl ./run.sh` with matched workloads.

## Learn more

- [User guide](docs/user-guide.md): controls, units, grouping, missing data, and troubleshooting.
- [Tests and benchmarks](tests/README.md): core checks, real native flows, and reproducible measurement commands.
- [Validation summary](docs/validation.md): results and limits of the initial verification.
- [OpenSpec change](openspec/changes/build-local-task-manager/proposal.md): requirements, design, and implementation checklist.
- [Publication checklist](docs/publishing.md): rules for reviewing public content.

## Remove the launcher

The installer prints its exact paths. Defaults are:

```text
~/.local/bin/workstation-monitor
~/.local/share/applications/local.workstation.Monitor.desktop
```

Remove only those app-owned files if you no longer want the launcher. Optional preferences are in `~/.config/workstation-monitor/preferences.json`; XDG environment settings can change these locations. There is no service or autostart entry to disable. The project and its `.venv` can remain for later use.
