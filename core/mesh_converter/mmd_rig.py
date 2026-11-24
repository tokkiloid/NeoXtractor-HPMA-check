"""MMD bone setup for PMX exports.

Bones named in the bone table (bone_names) are arranged into the usual MMD chains, with 全ての親, センター,
グルーブ, leg IK and D bones that follow the IK legs, and the semi-standard bones MMD motions use: 腰 with its
腰キャンセル, 足IK親, 肩P / 肩C, the arm and wrist twists (腕捩, 手捩) and 手先 / ダミー. Other bones keep their
parents. Bone tails and display frames are added too.
"""

from __future__ import annotations

import math

SETTING = "pmx_export.mmd_rig"
LABEL = "MMD bone setup on PMX export (IK legs, センター, semi-standard bones, display frames)"
SHOULDER_SETTING = "pmx_export.raise_shoulders"
SHOULDER_LABEL = "Raise shoulder bones (cleaner raised arms)"
SIDES = ("左", "右")
FINGERS = ("親指", "人指", "中指", "薬指", "小指")
# The 先 tip past each finger's last joint: (joint before, last joint, reach as a share of that last segment)
FINGER_TIPS = {
    "親指": ("１", "２", 1.0),
    "人指": ("２", "３", 0.6),
    "中指": ("２", "３", 0.6),
    "薬指": ("２", "３", 0.6),
    "小指": ("２", "３", 0.6),
}
FINGER_ENGLISH = {"親指": "thumb", "人指": "index", "中指": "middle", "薬指": "ring", "小指": "little"}
LEG_FK = {"足D": "足", "ひざD": "ひざ", "足首D": "足首"}
# Twist bones: (twist, the bone it turns, the bone it leads to); the twist sits 60 % of the way, its three helpers
# copy a quarter, half and three quarters of it, and the skin between the joints is shared out among them
TWISTS = (("腕捩", "腕", "ひじ"), ("手捩", "ひじ", "手首"))
TWIST_AT = 0.6
TWIST_HELPERS = ((1, 0.32, 0.25), (2, 0.52, 0.5), (3, 0.72, 0.75))  # number, place along the bone, share copied
TWIST_FULL = 0.92  # past here the skin turns with the whole twist


def _switch(key, settings) -> bool:
    """A PMX export switch from the app's settings; on when there are no settings or the key is unset."""
    if settings is None:
        try:
            from PySide6 import QtWidgets

            app = QtWidgets.QApplication.instance()
            settings = app.property("settings_manager") if app is not None else None
        except ImportError:
            settings = None
    try:
        return bool(settings.get(key, True)) if settings is not None else True
    except Exception:
        return True


def enabled(settings=None) -> bool:
    return _switch(SETTING, settings)


def shoulders_enabled(settings=None) -> bool:
    return _switch(SHOULDER_SETTING, settings)


def _chain() -> dict[str, list[str]]:
    """MMD name -> preferred parents (first one present wins)."""
    chain = {
        "上半身": ["腰", "グルーブ"],
        "上半身2": ["上半身"],
        "首": ["上半身2", "上半身"],
        "頭": ["首"],
        "下半身": ["腰", "グルーブ"],
    }
    for s in SIDES:
        chain.update(
            {
                f"{s}目": ["頭"],
                f"{s}肩": [f"{s}肩P", "上半身2", "上半身"],
                f"{s}腕": [f"{s}肩C", f"{s}肩", "上半身2"],
                f"{s}ひじ": [f"{s}腕捩", f"{s}腕"],
                f"{s}手首": [f"{s}手捩", f"{s}ひじ"],
                f"{s}足D": [f"腰キャンセル{s}", "下半身"],
                f"{s}ひざD": [f"{s}足D"],
                f"{s}足首D": [f"{s}ひざD"],
                f"{s}足先EX": [f"{s}足首D"],
            }
        )
        for finger in FINGERS:
            first = "０" if finger == "親指" else "１"
            order = ["０", "１", "２", "３"] if finger == "親指" else ["１", "２", "３"]
            previous = f"{s}手首"
            for step in order[order.index(first) :]:
                chain[f"{s}{finger}{step}"] = [previous]
                previous = f"{s}{finger}{step}"
    return chain


def vmd_name(name: str) -> str:
    """The bone a baked motion should key in a rigged model: the IK legs' FK bones instead of the D bones."""
    for side in SIDES:
        for deform, fk in LEG_FK.items():
            if name == f"{side}{deform}":
                return f"{side}{fk}"
    return name


IK_BONES = ("左足ＩＫ", "右足ＩＫ", "左つま先ＩＫ", "右つま先ＩＫ")


def build(bones, translated_names):
    """
    bones: pymeshio pmx.Bone list (parents before children, PMX space). translated_names: names that came
    from the translation table. Returns (bones in their new order, {old index: new index}, display slots).
    """
    from pymeshio import common, pmx

    names = [b.name for b in bones]
    index = {n: i for i, n in enumerate(names)}
    translated = {n for n in translated_names if n in index}
    if not translated:
        return bones, {i: i for i in range(len(bones))}, None
    chain = _chain()
    pos = {n: bones[i].position for n, i in index.items()}

    def vec(p):
        return common.Vector3(p.x, p.y, p.z)

    def new_bone(name, english, position, rotate=True, move=False, visible=True, operable=True):
        bone = pmx.Bone(name=name, english_name=english, position=vec(position), parent_index=-1, layer=0, flag=0)
        bone.setFlag(pmx.BONEFLAG_CAN_ROTATE, rotate)
        bone.setFlag(pmx.BONEFLAG_CAN_TRANSLATE, move)
        bone.setFlag(pmx.BONEFLAG_IS_VISIBLE, visible)
        bone.setFlag(pmx.BONEFLAG_CAN_MANIPULATE, operable)
        return bone

    nodes = list(bones)
    parent_name: dict[int, str | None] = {}
    for i, bone in enumerate(bones):
        parent_name[i] = names[bone.parent_index] if 0 <= bone.parent_index < len(bones) else None

    def add(bone, parent):
        nodes.append(bone)
        parent_name[len(nodes) - 1] = parent
        index[bone.name] = len(nodes) - 1
        return len(nodes) - 1

    hip = pos.get("下半身") or pos.get("上半身")
    hip_y = hip.y if hip is not None else 10.0
    origin = common.Vector3(0.0, 0.0, 0.0)
    add(new_bone("全ての親", "mother", origin, move=True), None)
    add(new_bone("センター", "center", common.Vector3(0.0, hip_y * 0.7, 0.0), move=True), "全ての親")
    add(new_bone("グルーブ", "groove", common.Vector3(0.0, hip_y * 0.75, 0.0), move=True), "センター")

    # Semi-standard bones. Where they sit is set again by place_semi_standard once the shoulders are raised.
    if "上半身" in index and "下半身" in index:
        add(new_bone("腰", "waist", common.Vector3(0.0, hip_y * 0.8, hip.z)), "グルーブ")
    for s in SIDES:
        side = "L" if s == "左" else "R"
        if "腰" in index and f"{s}足D" in index:
            add(new_bone(f"腰キャンセル{s}", f"waist cancel_{side}", pos[f"{s}足D"], visible=False), "下半身")
        if f"{s}肩" in index and f"{s}腕" in index:
            add(new_bone(f"{s}肩P", f"shoulderP_{side}", pos[f"{s}肩"]), "上半身2" if "上半身2" in index else "上半身")
            add(new_bone(f"{s}肩C", f"shoulderC_{side}", pos[f"{s}腕"], visible=False), f"{s}肩")
        for twist, bone, child in TWISTS:
            if f"{s}{bone}" in index and f"{s}{child}" in index:
                english = f"{'arm' if twist == '腕捩' else 'wrist'} twist_{side}"
                add(new_bone(f"{s}{twist}", english, pos[f"{s}{bone}"]), f"{s}{bone}")
                for number, _place, _share in TWIST_HELPERS:
                    helper = new_bone(f"{s}{twist}{number}", f"{english}{number}", pos[f"{s}{bone}"], visible=False)
                    add(helper, f"{s}{bone}")
        if f"{s}手首" in index:
            add(new_bone(f"{s}手先", f"hand tip_{side}", pos[f"{s}手首"], visible=False), f"{s}手首")
            add(new_bone(f"{s}ダミー", f"dummy_{side}", pos[f"{s}手首"], move=True), f"{s}手首")

    # Translated bones into the MMD chains; untranslated roots under 全ての親
    for name in translated:
        for parent in chain.get(name, []):
            if parent in index:
                parent_name[index[name]] = parent
                break
    for i in range(len(bones)):
        if parent_name[i] is None:
            parent_name[i] = "全ての親"

    # IK legs: FK bones at the D bones, IK handles at ankle and toe; D bones copy the FK rotation
    ik_specs = []
    for s in SIDES:
        if not all(f"{s}{d}" in index for d in ("足D", "ひざD", "足首D")):
            continue
        add(
            new_bone(f"{s}足", f"leg_{'L' if s == '左' else 'R'}", pos[f"{s}足D"]),
            f"腰キャンセル{s}" if f"腰キャンセル{s}" in index else "下半身" if "下半身" in index else "グルーブ",
        )
        add(new_bone(f"{s}ひざ", f"knee_{'L' if s == '左' else 'R'}", pos[f"{s}ひざD"]), f"{s}足")
        add(new_bone(f"{s}足首", f"ankle_{'L' if s == '左' else 'R'}", pos[f"{s}足首D"]), f"{s}ひざ")
        ankle = pos[f"{s}足首D"]
        joint = pos.get(f"{s}足先EX") or ankle
        # つま先 at the tip of the foot on the ground, ahead of the toe joint
        reach = max(abs(joint.z - ankle.z), 0.3) * 0.7
        toe_pos = common.Vector3(
            joint.x + (joint.x - ankle.x) * 0.3,
            max(0.0, min(joint.y, 0.3)),
            joint.z - reach if joint.z <= ankle.z else joint.z + reach,
        )
        add(
            new_bone(f"{s}つま先", f"toe_{'L' if s == '左' else 'R'}", toe_pos, visible=False, operable=False),
            f"{s}足首",
        )
        ground = common.Vector3(ankle.x, 0.0, ankle.z)
        add(new_bone(f"{s}足IK親", f"leg IKP_{'L' if s == '左' else 'R'}", ground, move=True), "全ての親")
        add(new_bone(f"{s}足ＩＫ", f"leg IK_{'L' if s == '左' else 'R'}", ankle, move=True), f"{s}足IK親")
        add(new_bone(f"{s}つま先ＩＫ", f"toe IK_{'L' if s == '左' else 'R'}", toe_pos, move=True), f"{s}足ＩＫ")
        ik_specs.append(s)

    # 両目 above the eyes, turning both of them (付与), and the hidden 先 tips MMD rigs end their chains with
    # (laid out like the TDA rig and 葵: 両目 ~1.4 above the eyes, a tip past the last joint of each finger)
    if all(f"{s}目" in index for s in SIDES) and "頭" in index:
        eye_y = (pos["左目"].y + pos["右目"].y) / 2
        eye_z = (pos["左目"].z + pos["右目"].z) / 2
        both = common.Vector3(0.0, eye_y * 1.085, eye_z)
        add(new_bone("両目", "eyes", both), "頭")
        add(new_bone("両目先", "eyes tip", common.Vector3(0.0, both.y, eye_z - eye_y * 0.045), visible=False), "両目")
        for s in SIDES:
            eye = pos[f"{s}目"]
            add(
                new_bone(
                    f"{s}目先",
                    f"eye tip_{'L' if s == '左' else 'R'}",
                    common.Vector3(eye.x, eye.y, eye.z - eye_y * 0.025),
                    visible=False,
                ),
                f"{s}目",
            )
    for s in SIDES:
        for finger, (before, last, reach) in FINGER_TIPS.items():
            first, end = pos.get(f"{s}{finger}{before}"), pos.get(f"{s}{finger}{last}")
            if first is None or end is None:
                continue
            tip = common.Vector3(
                end.x + (end.x - first.x) * reach, end.y + (end.y - first.y) * reach, end.z + (end.z - first.z) * reach
            )
            english = f"{FINGER_ENGLISH[finger]} tip_{'L' if s == '左' else 'R'}"
            add(new_bone(f"{s}{finger}先", english, tip, visible=False), f"{s}{finger}{last}")

    # Order: parents first, IK handles early, D bones after the legs they copy
    children: dict[str | None, list[int]] = {}
    for i in range(len(nodes)):
        children.setdefault(parent_name[i], []).append(i)
    order: list[int] = []
    seen = set()

    def visit(i):
        if i in seen:
            return
        seen.add(i)
        order.append(i)
        kids = children.get(nodes[i].name, [])
        # MMD deforms in bone order: IK handles first so the legs are solved before
        # anything reads them, then the FK legs, then the D bones that copy them (付与)
        kids.sort(
            key=lambda k: (
                nodes[k].name != "両目",
                nodes[k].name not in IK_BONES and not nodes[k].name.endswith("足IK親"),
                nodes[k].name.endswith(("D", "EX")),
                k,
            )
        )  # 両目 before the eyes it turns
        for k in kids:
            visit(k)

    visit(index["全ての親"])
    for i in range(len(nodes)):  # anything left keeps its place at the end
        visit(i)
    new_of = {old: new for new, old in enumerate(order)}
    by_name = {nodes[old].name: new for old, new in new_of.items()}
    result = [nodes[old] for old in order]
    for old, bone in zip(order, result):
        parent = parent_name[old]
        bone.parent_index = by_name[parent] if parent in by_name else -1

    # Grant (付与) and IK
    for s in ik_specs:
        for deform, fk in LEG_FK.items():
            d = result[by_name[f"{s}{deform}"]]
            d.effect_index = by_name[f"{s}{fk}"]
            d.effect_factor = 1.0
            d.setFlag(pmx.BONEFLAG_IS_EXTERNAL_ROTATION, True)
        leg_ik = result[by_name[f"{s}足ＩＫ"]]
        leg_ik.setFlag(pmx.BONEFLAG_IS_IK, True)
        knee = pmx.IkLink(
            by_name[f"{s}ひざ"], 1, common.Vector3(-math.pi, 0.0, 0.0), common.Vector3(-0.008727, 0.0, 0.0)
        )
        leg_ik.ik = pmx.Ik(by_name[f"{s}足首"], 40, 2.0, [knee, pmx.IkLink(by_name[f"{s}足"], 0)])
        toe_ik = result[by_name[f"{s}つま先ＩＫ"]]
        toe_ik.setFlag(pmx.BONEFLAG_IS_IK, True)
        toe_ik.ik = pmx.Ik(by_name[f"{s}つま先"], 3, 4.0, [pmx.IkLink(by_name[f"{s}足首"], 0)])
    grants = [(f"腰キャンセル{s}", "腰", -1.0) for s in SIDES] + [(f"{s}肩C", f"{s}肩P", -1.0) for s in SIDES]
    grants += [
        (f"{s}{twist}{number}", f"{s}{twist}", share)
        for s in SIDES
        for twist, _bone, _child in TWISTS
        for number, _place, share in TWIST_HELPERS
    ]
    for name, source, factor in grants:
        if name in by_name and source in by_name:
            bone = result[by_name[name]]
            bone.effect_index = by_name[source]
            bone.effect_factor = factor
            bone.setFlag(pmx.BONEFLAG_IS_EXTERNAL_ROTATION, True)
    if "両目" in by_name:
        for s in SIDES:
            eye = result[by_name[f"{s}目"]]
            eye.effect_index = by_name["両目"]
            eye.effect_factor = 1.0
            eye.setFlag(pmx.BONEFLAG_IS_EXTERNAL_ROTATION, True)

    # Deform layer 1 for the IK handles, the D bones and everything under them:
    # MMD then solves the IK only after 下半身 and the FK legs are placed for the frame, and the D chain
    # copies the solved legs. On layer 0 the IK ran before 下半身 and crossed the legs in TransformView.
    late = {by_name[n] for s in ik_specs for n in (f"{s}足ＩＫ", f"{s}つま先ＩＫ", f"{s}足D", f"{s}ひざD", f"{s}足首D")}
    for i, bone in enumerate(result):  # parents come first, so one pass reaches all descendants
        if i in late or bone.parent_index in late:
            late.add(i)
            bone.layer = 1

    # Tails down each chain
    tails = {"上半身": "上半身2", "上半身2": "首", "首": "頭", "全ての親": "センター"}
    for s in SIDES:
        tails.update(
            {
                f"{s}肩": f"{s}腕",
                f"{s}腕": f"{s}ひじ",
                f"{s}ひじ": f"{s}手首",
                f"{s}足": f"{s}ひざ",
                f"{s}ひざ": f"{s}足首",
                f"{s}足首": f"{s}つま先",
                f"{s}足D": f"{s}ひざD",
                f"{s}ひざD": f"{s}足首D",
            }
        )
    for parent, child in tails.items():
        if parent in by_name and child in by_name:
            bone = result[by_name[parent]]
            bone.tail_index = by_name[child]
            bone.setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, True)
    # Offset tails so the control bones show a direction in PMX Editor / MMD
    offsets = {"センター": (0.0, -hip_y * 0.6, 0.0), "グルーブ": (0.0, hip_y * 0.15, 0.0)}
    for s in ik_specs:
        offsets[f"{s}足ＩＫ"] = (0.0, 0.0, hip_y * 0.12)
        offsets[f"{s}つま先ＩＫ"] = (0.0, -hip_y * 0.08, 0.0)
    for name, (x, y, z) in offsets.items():
        if name in by_name:
            bone = result[by_name[name]]
            bone.setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, False)
            bone.tail_position = common.Vector3(x, y, z)
    # Legs and their D bones only rotate (only 全ての親, センター, グルーブ and the IK handles move)
    for s in ik_specs:
        for name in ("足", "ひざ", "足首", "足D", "ひざD", "足首D", "足先EX"):
            if f"{s}{name}" in by_name:
                result[by_name[f"{s}{name}"]].setFlag(pmx.BONEFLAG_CAN_TRANSLATE, False)
    # So do the upper body, neck, head, arms and fingers, as in MMD models (VMD position keys on them are ignored)
    arm_stems = ("肩", "腕", "ひじ", "手首", "親指", "人指", "中指", "薬指", "小指")
    for bone in result:
        side_free = bone.name[1:] if bone.name[:1] in "左右" else ""
        if bone.name in ("上半身", "上半身2", "下半身", "腰", "首", "頭") or (
            side_free and side_free.startswith(arm_stems) and not side_free.startswith("ダミー")
        ):
            bone.setFlag(pmx.BONEFLAG_CAN_TRANSLATE, False)

    # Display frames
    arm_frame = ("肩P", "肩", "腕", "腕捩", "ひじ", "手捩", "手首", "ダミー")
    groups = [
        ("センター", "Center", ["センター", "グルーブ"]),
        ("ＩＫ", "IK", [n for n in (*IK_BONES, "左足IK親", "右足IK親") if n in by_name]),
        ("体(上)", "Upper body", ["上半身", "上半身2", "首", "頭", "両目", "左目", "右目"]),
        ("腕", "Arms", [f"{s}{b}" for s in SIDES for b in arm_frame]),
        ("指", "Fingers", [n for n in by_name if any(f in n for f in FINGERS) and not n.endswith("先")]),
        ("体(下)", "Lower body", ["腰", "下半身"]),
        ("足", "Legs", [f"{s}{b}" for s in SIDES for b in ("足", "ひざ", "足首", "足D", "ひざD", "足首D", "足先EX")]),
    ]
    used = {"全ての親"}
    slots = [pmx.DisplaySlot("Root", "Root", 1, [(0, by_name["全ての親"])]), pmx.DisplaySlot("表情", "Exp", 1, [])]
    for name, english, members in groups:
        refs = [(0, by_name[m]) for m in members if m in by_name and m not in used]
        used.update(m for m in members if m in by_name)
        if refs:
            slots.append(pmx.DisplaySlot(name, english, 0, refs))
    others = [(0, i) for i, bone in enumerate(result) if bone.name not in used and not bone.name.endswith("つま先")]
    if others:
        slots.append(pmx.DisplaySlot("その他", "Others", 0, others))
    return result, new_of, slots


def merge_twin_helpers(mesh):
    """
    Weights of the game's helper bones that double a real limb bone (bone_l_upperarm next to bip001_l_upperarm:
    the shoulder pad of some coats) moved onto that limb bone, so the piece turns with the arm in MMD instead of
    staying behind (nothing drives the helper there). Returns `mesh` itself when there is nothing to merge.
    """
    names = [str(n).lower() for n in (mesh.bone_name or [])]
    position = {n: i for i, n in enumerate(names)}
    twins = {}
    for i, name in enumerate(names):
        if name.startswith("bone_"):
            target = position.get("bip001_" + name[len("bone_") :])
            if target is not None:
                twins[i] = target
    if not twins or not mesh.vertex_bone:
        return mesh
    joints, weights, changed = [], [], False
    for bones, values in zip(mesh.vertex_bone, mesh.vertex_weight):
        merged: dict[int, float] = {}
        for bone, weight in zip(bones, values):
            if weight > 0 and bone in twins:
                changed = True
            bone = twins.get(bone, bone)
            merged[bone] = merged.get(bone, 0.0) + float(weight)
        pairs = sorted(((w, b) for b, w in merged.items()), reverse=True)[:4]
        while len(pairs) < len(bones):
            pairs.append((0.0, 0))
        joints.append(tuple(b for _w, b in pairs))
        weights.append(tuple(w for w, _b in pairs))
    if not changed:
        return mesh
    import copy

    merged_mesh = copy.copy(mesh)
    merged_mesh.vertex_bone = joints
    merged_mesh.vertex_weight = weights
    return merged_mesh


# Shoulder heights taken from a reference MMD rig: 腕 3.7 % and 肩 0.9 % of the body's height below 首
ARM_BELOW_NECK = 0.037
SHOULDER_BELOW_NECK = 0.009


def raise_shoulders(model, report=None) -> float:
    """
    Lift 肩 and 腕 to where MMD rigs usually have them. The game's clavicle / upper-arm pivots sit lower (腕 about
    5.5 % of the height below the neck instead of 3.7 %), so raising an arm in MMD folds the shoulder and drags the
    sleeve. Both sides get the same lift; bones are never lowered. Only the bone positions move (not the mesh or
    the weights). Returns the upper-arm lift applied.
    """
    from pymeshio import common

    bones = model.bones
    index = {bone.name: i for i, bone in enumerate(bones)}
    if not all(n in index for n in ("首", "頭", "左肩", "右肩", "左腕", "右腕")):
        return 0.0
    feet = [bones[index[n]].position.y for n in ("左つま先", "右つま先", "左足首", "右足首") if n in index]
    if not feet:
        return 0.0
    neck = bones[index["首"]].position.y
    height = bones[index["頭"]].position.y - min(feet)
    if height <= 0:
        return 0.0

    def lift(names, below):
        target = neck - below * height
        current = sum(bones[index[n]].position.y for n in names) / len(names)
        return max(0.0, min(target - current, 0.05 * height))

    arm = lift(("左腕", "右腕"), ARM_BELOW_NECK)
    shoulder = lift(("左肩", "右肩"), SHOULDER_BELOW_NECK)
    for names, amount in ((("左腕", "右腕"), arm), (("左肩", "右肩"), shoulder)):
        for name in names:
            bone = bones[index[name]]
            bone.position = common.Vector3(bone.position.x, bone.position.y + amount, bone.position.z)
    if report is not None and (arm or shoulder):
        report.append(f"upper arms raised by {arm:.3f}, shoulders by {shoulder:.3f}")
    return arm


def place_semi_standard(model) -> None:
    """
    Put the semi-standard bones where MMD rigs have them, once the shoulders are raised: 肩P at 肩, 肩C at 腕, the
    twists along their bones (turning about the bone), 手先 and ダミー at the hand. The arms, hands and fingers get
    local axes (x along the bone, z to the back), and the skin between the joints is shared out among the twists.
    """
    import numpy as np
    from pymeshio import common, pmx

    bones = model.bones
    index = {bone.name: i for i, bone in enumerate(bones)}

    def at(name):
        v = bones[index[name]].position
        return np.array([v.x, v.y, v.z], float)

    def put(name, point):
        bones[index[name]].position = common.Vector3(*(float(c) for c in point))

    for s in SIDES:
        if f"{s}肩P" in index:  # on top of 肩: no tail of its own, as in MMD rigs
            put(f"{s}肩P", at(f"{s}肩"))
            shoulder = bones[index[f"{s}肩P"]]
            shoulder.setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, False)
            shoulder.tail_position = common.Vector3(0.0, 0.0, 0.0)
        if f"{s}足IK親" in index and f"{s}足ＩＫ" in index:  # points up at the IK handle it carries
            ground = bones[index[f"{s}足IK親"]]
            ground.tail_index = index[f"{s}足ＩＫ"]
            ground.setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, True)
        if f"{s}肩C" in index:
            put(f"{s}肩C", at(f"{s}腕"))
        for twist, bone, child in TWISTS:
            if f"{s}{twist}" not in index:
                continue
            start, end = at(f"{s}{bone}"), at(f"{s}{child}")
            put(f"{s}{twist}", start + (end - start) * TWIST_AT)
            axis = (end - start) / max(np.linalg.norm(end - start), 1e-9)
            turning = bones[index[f"{s}{twist}"]]
            turning.setFlag(pmx.BONEFLAG_HAS_FIXED_AXIS, True)
            turning.fixed_axis = common.Vector3(*(float(c) for c in axis))
            turning.setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, False)  # no tail, as in MMD rigs: it only turns in place
            turning.tail_position = common.Vector3(0.0, 0.0, 0.0)
            for number, place, _share in TWIST_HELPERS:
                put(f"{s}{twist}{number}", start + (end - start) * place)
        if f"{s}手先" in index:
            wrist, elbow = at(f"{s}手首"), at(f"{s}ひじ") if f"{s}ひじ" in index else at(f"{s}手首")
            middle = f"{s}中指１"
            tip = wrist + (at(middle) - wrist) * 0.85 if middle in index else wrist + (wrist - elbow) * 0.3
            put(f"{s}手先", tip)
            hand = bones[index[f"{s}手首"]]
            hand.tail_index = index[f"{s}手先"]
            hand.setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, True)
            if f"{s}ダミー" in index:  # below the palm, where a held prop sits
                drop = 0.25 * np.linalg.norm(wrist - elbow)
                put(f"{s}ダミー", wrist + (tip - wrist) * 0.1 - np.array([0.0, drop, 0.0]))

    # Local axes: x toward the bone's tail, z the back (0, 0, 1) made square to it
    limbs = ("肩", "腕", "ひじ", "手首", *FINGERS)
    for bone in bones:
        stem = bone.name[1:] if bone.name[:1] in "左右" else ""
        if not stem.startswith(limbs) or stem.endswith(("先", "P", "C")) or "捩" in stem:
            continue
        if bone.hasFlag(pmx.BONEFLAG_TAILPOS_IS_BONE):
            if not 0 <= bone.tail_index < len(bones):
                continue
            tail = bones[bone.tail_index].position
            direction = np.array([tail.x - bone.position.x, tail.y - bone.position.y, tail.z - bone.position.z])
        else:
            tail = bone.tail_position
            direction = np.array([tail.x, tail.y, tail.z], float)
        length = np.linalg.norm(direction)
        if length < 1e-6:
            continue
        x = direction / length
        z = np.array([0.0, 0.0, 1.0]) - x[2] * x
        if np.linalg.norm(z) < 1e-6:
            continue
        z /= np.linalg.norm(z)
        bone.setFlag(pmx.BONEFLAG_HAS_LOCAL_COORDINATE, True)
        bone.local_x_vector = common.Vector3(*(float(c) for c in x))
        bone.local_z_vector = common.Vector3(*(float(c) for c in z))

    _share_twist_weights(model, index, at)


def _share_twist_weights(model, index, at) -> None:
    """
    The skin of each upper arm and forearm moves onto its twist bones by where it sits along the bone: the bone's own
    up to 12 %, then blending through the three helpers (32, 52, 72 %) to the whole twist at 92 %. Skin also weighted
    to the body (shoulder, chest) is left as it is, so the armpits keep their shape.
    """
    import numpy as np
    from pymeshio import pmx

    arm_stems = ("腕", "ひじ", "手首", *FINGERS)
    for s in SIDES:
        allowed = {i for name, i in index.items() if name[:1] == s and name[1:].startswith(arm_stems)}
        for twist, bone, child in TWISTS:
            names = [f"{s}{bone}", f"{s}{child}", f"{s}{twist}"] + [f"{s}{twist}{n}" for n, _p, _s in TWIST_HELPERS]
            if not all(name in index for name in names):
                continue
            source = index[f"{s}{bone}"]
            start, end = at(f"{s}{bone}"), at(f"{s}{child}")
            span = end - start
            reach = float(np.dot(span, span)) or 1.0
            anchors = [(TWIST_HELPERS[0][1] - 0.2, source)]
            anchors += [(place, index[f"{s}{twist}{n}"]) for n, place, _share in TWIST_HELPERS]
            anchors += [(TWIST_FULL, index[f"{s}{twist}"])]
            for vertex in model.vertices:
                weights = _weights(vertex.deform)
                total = dict(weights)
                if source not in total or not set(total) <= allowed:
                    continue
                point = np.array([vertex.position.x, vertex.position.y, vertex.position.z])
                t = float(np.dot(point - start, span)) / reach
                shares = _anchor_shares(anchors, t)
                moved = total.pop(source)
                for target, share in shares:
                    total[target] = total.get(target, 0.0) + moved * share
                kept = [(i, w) for i, w in total.items() if w > 1e-6]
                if len(kept) > 4:
                    continue
                vertex.deform = _deform(kept, pmx)


def _anchor_shares(anchors, t):
    """[(bone, share)] at t along the bone, blending linearly between the two anchors around it."""
    if t <= anchors[0][0]:
        return [(anchors[0][1], 1.0)]
    for (low, below), (high, above) in zip(anchors, anchors[1:]):
        if t <= high:
            mix = (t - low) / (high - low)
            return [(below, 1.0 - mix), (above, mix)]
    return [(anchors[-1][1], 1.0)]


def _weights(deform) -> list:
    if hasattr(deform, "index3"):
        pairs = [(deform.index0, deform.weight0), (deform.index1, deform.weight1)]
        pairs += [(deform.index2, deform.weight2), (deform.index3, deform.weight3)]
    elif hasattr(deform, "index1"):
        pairs = [(deform.index0, deform.weight0), (deform.index1, 1.0 - deform.weight0)]
    else:
        pairs = [(deform.index0, 1.0)]
    merged: dict = {}
    for i, w in pairs:
        if w > 0:
            merged[i] = merged.get(i, 0.0) + w
    return list(merged.items())


def _deform(pairs, pmx):
    total = sum(w for _i, w in pairs) or 1.0
    pairs = [(i, w / total) for i, w in pairs]
    if len(pairs) == 1:
        return pmx.Bdef1(pairs[0][0])
    if len(pairs) == 2:
        return pmx.Bdef2(pairs[0][0], pairs[1][0], pairs[0][1])
    pairs += [(0, 0.0)] * (4 - len(pairs))
    return pmx.Bdef4(*(i for i, _w in pairs), *(w for _i, w in pairs))


def hips_to_center(names: list[str], keys: list) -> tuple[list[str], list]:
    """
    A baked motion's hip movement on センター, as MMD motions have it: 上半身 and 下半身 only turn in MMD models, so
    the position keys the game's pelvis gives them move to a センター key (the whole body moves with it).
    """
    if "下半身" not in names:
        return names, keys
    hips = names.index("下半身")
    upper = names.index("上半身") if "上半身" in names else -1
    names = list(names)
    if "センター" not in names:
        names.append("センター")
    center = names.index("センター")
    moved = []
    for bone, frame, position, rotation in keys:
        if bone == hips:
            moved.append((center, frame, tuple(position), (0.0, 0.0, 0.0, 1.0)))
        if bone in (hips, upper):
            position = (0.0, 0.0, 0.0)
        moved.append((bone, frame, position, rotation))
    return names, moved


def remove_unused(model) -> int:
    """
    Drop the game's bones that move nothing in this export (no vertex weight on them or anything below them): the
    cape, scarf, sleeve, hair and prop bones of pieces that aren't included, so each export carries only the bones
    its own pieces use. MMD skips motion keys for bones a model doesn't have, so motions still load. MMD-named bones
    (センター, the IK and FK legs that drive the D bones, the eyes) and every ancestor of a kept bone stay.
    Vertex weights, parents, tails, IK, grants and display frames are renumbered. Returns how many were removed.
    """
    from pymeshio import common, pmx

    bones = model.bones
    used = set()
    for vertex in model.vertices:
        deform = vertex.deform
        for slot in range(4):
            bone = getattr(deform, f"index{slot}", None)
            weight = getattr(deform, f"weight{slot}", 1.0 if slot == 0 else 0.0)
            if bone is not None and (weight is None or weight > 0):
                used.add(bone)
    children: dict[int, list[int]] = {}
    for i, bone in enumerate(bones):
        children.setdefault(bone.parent_index, []).append(i)
    keep_memo: dict[int, bool] = {}

    def keep(i):
        if i not in keep_memo:
            keep_memo[i] = (not bones[i].name.isascii()) or i in used or any(keep(c) for c in children.get(i, []))
        return keep_memo[i]

    kept = [i for i in range(len(bones)) if keep(i)]
    # IK targets / links and grant sources of kept bones are kept too
    extra = set()
    for i in kept:
        bone = bones[i]
        if bone.ik is not None:
            extra.add(bone.ik.target_index)
            extra.update(link.bone_index for link in bone.ik.link)
        if bone.hasFlag(pmx.BONEFLAG_IS_EXTERNAL_ROTATION) or bone.hasFlag(pmx.BONEFLAG_IS_EXTERNAL_TRANSLATION):
            extra.add(bone.effect_index)
    kept = sorted(set(kept) | {i for i in extra if 0 <= i < len(bones)})
    if len(kept) == len(bones):
        return 0
    remap = {old: new for new, old in enumerate(kept)}

    def ancestor_kept(i):
        while i >= 0 and i not in remap:
            i = bones[i].parent_index
        return remap.get(i, -1)

    new_bones = []
    for old in kept:
        bone = bones[old]
        bone.parent_index = ancestor_kept(bone.parent_index) if bone.parent_index >= 0 else -1
        if bone.hasFlag(pmx.BONEFLAG_TAILPOS_IS_BONE):
            if bone.tail_index in remap:
                bone.tail_index = remap[bone.tail_index]
            else:
                bone.setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, False)
                bone.tail_position = common.Vector3(0.0, 0.0, 0.0)
        if bone.ik is not None:
            bone.ik.target_index = remap.get(bone.ik.target_index, 0)
            for link in bone.ik.link:
                link.bone_index = remap.get(link.bone_index, 0)
        if bone.hasFlag(pmx.BONEFLAG_IS_EXTERNAL_ROTATION) or bone.hasFlag(pmx.BONEFLAG_IS_EXTERNAL_TRANSLATION):
            bone.effect_index = remap.get(bone.effect_index, -1)
        new_bones.append(bone)
    for vertex in model.vertices:
        deform = vertex.deform
        for slot in range(4):
            name = f"index{slot}"
            if hasattr(deform, name):
                setattr(deform, name, remap.get(getattr(deform, name), 0))
    for slot in model.display_slots or []:
        refs = getattr(slot, "references", None)
        if refs:
            slot.references = [
                (kind, remap[index]) if kind == 0 else (kind, index)
                for kind, index in refs
                if kind != 0 or index in remap
            ]
    model.bones = new_bones
    return len(bones) - len(new_bones)


def link_tails(bones, only=None) -> None:
    """
    Give every visible bone whose tail is still a zero-length offset a tail:
    the one child that continues its chain (人指１ -> 人指２, l_hair01_01 -> l_hair01_02), else a short offset
    continuing the bone's own direction (fingertips, 手首 like a 手先, hair and cloth tips). 頭 points up,
    目 forward, 下半身 down between the legs, 足首D at 足先EX. With `only` (a set of names), the other bones
    keep their zero-length tail.
    """
    import re
    from pymeshio import common, pmx

    count = len(bones)
    children: dict[int, list[int]] = {}
    for i, bone in enumerate(bones):
        if 0 <= bone.parent_index < count:
            children.setdefault(bone.parent_index, []).append(i)
    by_name = {bone.name: i for i, bone in enumerate(bones)}

    def vec(i):
        p = bones[i].position
        return (p.x, p.y, p.z)

    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def length(v):
        return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])

    def unset(bone):
        if bone.hasFlag(pmx.BONEFLAG_TAILPOS_IS_BONE):
            return False
        tail = getattr(bone, "tail_position", None)
        return tail is None or (abs(tail.x) + abs(tail.y) + abs(tail.z)) < 1e-6

    def set_bone(i, j):
        bones[i].tail_index = j
        bones[i].setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, True)

    def set_offset(i, v):
        bones[i].setFlag(pmx.BONEFLAG_TAILPOS_IS_BONE, False)
        bones[i].tail_position = common.Vector3(*v)

    def successor(name):
        """l_hair01_01 -> l_hair01_02, 人指１ -> 人指２ (the next number in the name)."""
        digits = "０１２３４５６７８９"
        if name and name[-1] in digits and name[-1] != "９":
            return name[:-1] + digits[digits.index(name[-1]) + 1]
        match = re.search(r"(\d+)$", name)
        if match:
            number = str(int(match.group(1)) + 1).zfill(len(match.group(1)))
            return name[: match.start(1)] + number
        return None

    def height():
        ys = [bone.position.y for bone in bones]
        return (max(ys) - min(ys)) if ys else 10.0

    tall = height() or 10.0
    for i, bone in enumerate(bones):
        if not unset(bone) or not bone.hasFlag(pmx.BONEFLAG_IS_VISIBLE) or bone.hasFlag(pmx.BONEFLAG_IS_IK):
            continue
        if only is not None and bone.name not in only:
            continue
        name = bone.name
        if name == "頭":
            set_offset(i, (0.0, tall * 0.09, 0.0))
            continue
        if name in ("左目", "右目", "両目"):
            if name + "先" in by_name:
                set_bone(i, by_name[name + "先"])
            else:
                set_offset(i, (0.0, 0.0, -tall * 0.03))
            continue
        if name == "下半身":
            legs = [by_name[n] for n in ("左足", "右足") if n in by_name]
            if legs:
                y = sum(bones[j].position.y for j in legs) / len(legs) - bone.position.y
                set_offset(i, (0.0, y if y < -tall * 0.02 else -tall * 0.06, 0.0))
                continue
        if name.endswith("足首D"):
            toe = by_name.get(name[:-3] + "足先EX")
            if toe is not None:
                set_bone(i, toe)
                continue
        here = vec(i)
        kids = [
            j
            for j in children.get(i, [])
            if length(sub(vec(j), here)) > 1e-4 and not bones[j].hasFlag(pmx.BONEFLAG_IS_IK)
        ]
        next_name = successor(name)
        chained = [j for j in kids if next_name and bones[j].name == next_name]
        if len(kids) == 1 and not name.endswith("手首"):
            set_bone(i, kids[0])
            continue
        if chained:
            set_bone(i, chained[0])
            continue
        # an end (or a fork such as the wrist): carry on in the bone's own direction
        parent = bone.parent_index
        if 0 <= parent < count:
            direction = sub(here, vec(parent))
            size = length(direction)
            if size > 1e-4:
                scale = min(0.5, tall * 0.04 / size) if not name.endswith("手首") else min(0.4, tall * 0.06 / size)
                set_offset(i, (direction[0] * scale, direction[1] * scale, direction[2] * scale))


def vmd_parents(names: list[str], parents: list[int]) -> list[int]:
    """
    Parents a motion must be baked against for the rigged PMX: translated bones use the MMD chains
    (unkeyed control bones such as グルーブ count as the root), everything else keeps its parent.
    """
    chain = _chain()
    index = {n: i for i, n in enumerate(names)}
    result = list(parents)
    for i, name in enumerate(names):
        for parent in chain.get(name, []):
            if parent in index:
                result[i] = index[parent]
                break
            if parent in ("グルーブ", "センター", "全ての親", "腰"):
                result[i] = -1
                break
    return result
