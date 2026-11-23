# NeoXtractor – Harry Potter: Magic Awakened build (source)

This branch is the full source of the HPMA build of NeoXtractor: real file names for most of the game's packs, the
Characters, Animations and Stages pages, the Scene Viewer, the Main Character Creator, MMD (PMX/VMD) export and the
game's sound names. It is made mostly for Harry Potter: Magic Awakened, though you can try it on other games built
on the NeoX engine. Just keep in mind that this fork was made with HPMA in mind only. I'd really appreciate help from
other fans, so we can make the creator as cool as possible.

Licensed under the GNU AGPL v3.0, like NeoXtractor: see [LICENSE](LICENSE). What was changed, and the third-party
data used, is listed in [NOTICE.md](NOTICE.md). No game files are included.

## Running from source

You need Python 3.12, [uv](https://docs.astral.sh/uv/) and a game install.

```
uv sync
uv run main.py
```

Pick the "Harry Potter: Magic Awakened" config, then open any `.npk` under the game's `res` folder. The
Characters, Animations and Stages pages are in the category list; the Scene Viewer and Main Character Creator are
under Tools.

## How to use

### Opening the game's files

1. In **Active Config**, pick **Harry Potter: Magic Awakened**.
2. **File → Open File** and choose a `.npk` from the game's `res` folder (for example `res\model\character.npk`).
3. The same pack in `res2`, `res3`, ... and the launcher's update folder (`Documents\res`) opens with it, and the
   files show their real names. To open one pack on its own, untick **File → Load all same-name related
   copies together (HPMA)** before opening.

The category list under the search box picks what the left side shows: the usual file types, plus **Audio**,
**Characters**, **Stages** and **Animations**. The search box at the top searches whichever of them is shown; the
Binary / Text / Slot boxes only apply to the file list and Characters, so Stages and Animations hide them.

### Characters

Choose **Characters** in the category list. The first scan of a pack takes a while (the progress bar has a
Cancel button); later scans of the same files are quicker. A cancelled scan starts again the next time you open
Characters.

- Folders follow the game's own layout. Each mesh lists the textures and materials it uses. Items show their
  English name and icon.
- The search box and the Binary / Text / Slot boxes filter this tree too. **Save Visible…** under the tree saves
  everything it shows, linked textures included.
- Right-click a selection to:
  - **Save selected / folder (including linked textures)…**: the raw files;
  - **Export all as one GLB… / PMX…**: everything selected in one model;
  - **Export each mesh separately**, **each folder as one file**, **faces** (face, eyes and eyebrows, optionally
    with every face shape), **hats only**, or **item icons (PNG)**;
  - **Add to Scene Viewer**, or open the **Main Character Creator** on a face folder.
- **Export options** in the same menu holds the PMX switches (see *PMX and MMD*).

### Main Character Creator

**Tools → Main Character Creator** (open any HPMA pack first, preferably `character.npk`, so the game folder is
known). It works like the game's wardrobe:

- **Female / Male** at the top; it opens on a random look.
- Pick a face, face shape, skin tone, makeup, eyes, hairstyle and hair dye, outfits and accessories from the
  list on the left. **Filter** narrows it by rarity or trait; the search box finds items by name.
- The **Layers** box hides single meshes from the preview and from exports. The two body buttons (top left)
  switch between the teenage size and the grown-up size, like in the game.
- **Wand** holds one of the game's wand skins in the right hand. **Pose** plays an idle pose in the 3D view
  (the wand follows the right hand). If you pick no pose, legendary and mythic outfits play their own idle, and
  lower tiers play the **Standard** pose, as in the game. A pose brings the props it needs, each playing its own
  animation, and props that belong to other poses are put away. A few poses put the wand away too, as they do in
  the game. The particle effects some poses have are not shown yet.
- **Owl**: picking an owl plays it landing on the hand, then the character holds it. Changing anything else ends
  it and the usual idle plays again; the owl comes back when you pick an owl again or choose the owl pose
  (持鸮而立), which shows the chosen owl on the hand.
- **Pet** rides on the character's shoulder or sits at their feet, playing its own idle whatever the pose; it stays
  until you pick **None**.
- **Export ▼** saves the character as GLB, PMX or OBJ, without animation, with the props the pose shows
  (**PMX options** are in the same menu).
  **Pose as VMD… / GLB…** in the same menu save the pose that plays (the picked one, or the outfit's own idle) on
  its own: a VMD for the exported PMX with TDA armature structure, or a GLB on the game's default character.
- **Save texture ▼** saves the baked face, eye, eyebrow and hair textures, and **Add to Scene Viewer** sends the
  character there.

### Scene Viewer

**Tools → Scene Viewer**. Add models with **Add to Scene Viewer** in the right-click menu of the file list or the
Characters tree (or select them and press **Ctrl+Shift+A**), from the creator, or from a stage.

- Right-click objects for **Assign Texture…**, **Auto-match Textures** (finds a model's own textures in the
  folder it belongs to), **Clear Texture** and **Remove**.
- **Show bones** and **Play animations** (works with Stages) change the view.
- **Export ▼** saves the whole scene as **GLB…** or **PMX…**, or **Animations (PMX + VMD)…**.

The Scene Viewer works as a "lite" character builder, but it is mostly meant for bringing stages into 3D programs.

### Stages

Open `scene.npk` (or a DLC such as `res_dlc1_hogsmeade.npk`) and choose **Stages** in the category
list. It lists that pack's stage scenes, grouped by stage; the models and textures they place are read from the
game's other packs automatically. With any other pack open, the page stays empty. To look at a stage,
open it in the Scene Viewer.

Select scenes, pick a format (GLB, PMX + textures, or glTF + .bin + textures) and press **Export Selected…**;
tick **Include collision / navigation helpers** to keep those meshes. **Open in Scene Viewer** loads one scene
with its textures already matched.

In the file list, selecting a scene file (`.scn`) previews the stage on the right with the **Scene Viewer** from
the viewer list; its **Open in Scene Viewer** button loads it into the Scene Viewer window.

### Animations

Open a pack that holds animations (for example `res\model\character.npk`) and choose **Animations** in the
category list: it lists that pack's clips by the game folder they live in. The selected clip
plays on its model in the viewer area, with its length, frames and bones shown over it (the box at the top right
picks another model from the same folder). Right-click a clip for **Export GLB…** (model with the clip),
**Export VMD…** (a motion for the PMX models), or **Export character animations (VMD / GLB)…** to
pick the male or female player character and export many clips at once, as VMD or GLB.

### Audio

Open `res\wwise.npk` and choose **Audio** in the category list. The sounds are sorted into folders: **english**
holds the voice lines, each under the sound bank that plays it (for example `english\vo_spell_battle`), **sounds**
the other sounds by bank, and **banks** the sound banks themselves. The search box finds sounds by name, folder or
bank. Select a sound to hear it in the preview, double-click it to open the **Audio Viewer** (which can also save it
as a playable Ogg file), or right-click for **Save selected…**, which keeps the folders.

### PMX and MMD

Every PMX export (Characters, creator, Scene Viewer) has a **PMX options** menu:

- **Translate bones to MMD names** and **MMD bone setup** (センター, IK legs, display frames), so most MMD motions
  work on the model (yaaaaa, HPMA dancing to K-pop);
- **Five fingers**: the game only rigs three fingers; this gives the ring and little fingers their own bones;
- **Body rigid bodies**: collision so hair and cloth physics don't fall through the body;
- **Raise shoulder bones** for cleaner raised arms: the game's rig has its shoulders lower than MMD motions
  expect.

Bone names come from a built-in table. To change them, put a `pmx_bone_names.xlsx`, `.csv` or `.txt` next to
NeoXtractor: first column the game's bone name, second the PMX name.

### Caches

The app keeps a few caches next to itself (`scan_cache\`, `item_links_cache.json`) so later scans are faster.
They are rebuilt when the game files change, and deleting them is safe.

---

*The original NeoXtractor README follows.*

# NeoXtractor

![Python versions](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/MarcosVLl2/NeoXtractor/ci.yml)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?logo=discord&logoColor=white)](https://discord.gg/eedXVqzmfn)

A Python tool for extracting, viewing, and converting files from NPK archives used by Netease's NeoX game engine.

THIS TOOL IS IN ITS EARLY STAGES, ANY HELP IS WELCOME! FEEL FREE TO OPEN A PULL REQUEST OR FORK THE REPOSITORY IF YOU WISH TO ADD SOMETHING OR FIX ANY ISSUE YOU SPOT

## Download

Download the latest release at [GitHub Releases](https://github.com/MarcosVLl2/NeoXtractor/releases)

### Bleeding edge builds

If you'd like to download the latest builds without waiting for a release, you can go to the [Actions](https://github.com/MarcosVLl2/NeoXtractor/actions) tab to see a list of automatic builds.

Find the build that you'd like to use, click it and download at the **Artifacts** section.

## Usage

### GUI

1. Run `neoxtractor.exe` directly to start in GUI mode.
2. Some games' NPK (EXPK) requires XOR key to be set. We have default profile for Onmyoji currently. To set XOR key, create a new config in Config Manager.
![Config Manager tutorial](assets/set-xor-key.png)
3. Open the NPK file.

#### Introduction

![GUI Overview](assets/gui-overview.png)

Main window is divided into two main parts: File list area and preview area.

In the file list area, you are able to:
- Select current config

  Note that every time you change the config, the current loaded NPK file will be unloaded.

- Filter entries inside NPK file
- View NPK's file list

Within the file list area, you can right click to operate on the selected entries. Currently, you can:
- Extract all selected entries
- Open selected entries with specific viewer
- Rename current entry

  You must select only one entry to rename the entry.

  New name of the entry is bind to entry's file signature. All names are saved in current active config.

### CLI

Command-line interface is still being worked on.

## Development

You will need [uv](https://github.com/astral-sh/uv) to properly setup the development environment.

1. Install dependencies
```bash
uv sync
```

2. Create virtual environment
```bash
uv venv
```

3. Enter virtual environment (required every time you start to work on the project)
```bash
# Linux
source .venv/bin/activate

# Windows
.venv/bin/activate.bat
```

## Have questions?

Feel free to join the Discord server (link at the top of this document) to ask them!

## Acknowledgements

**NeoX is an in-house game engine developed by Netease.**

**NeoXtractor is not affiliated with Netease.**

This tool is limited for educational purposes.