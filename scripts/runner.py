"""A compact, filled SVG platformer character with a twelve-pose run cycle.

``pose(action, phase, direction)`` returns joints in local SVG coordinates.
Phase is in cycles (0..1 for one run or breath). Feet use y=0 as the floor;
the standing character is approximately 48 units high. ``parts(joints)``
returns a stable ordered set of SVG paths, suitable for interpolating ``d``.
"""

import math


JOINTS = (
    "hip", "shoulder", "head",
    "elbow-far", "hand-far", "elbow-near", "hand-near",
    "knee-far", "foot-far", "knee-near", "foot-near",
)

WHITE = "#f3f8f7"
FAR = "#bfd3cf"
SHADOW = "#8ba8a4"
INK = "#17282b"


def _joints(hip, shoulder, head, far_arm, near_arm, far_leg, near_leg):
    dx, dy = shoulder[0]-hip[0], shoulder[1]-hip[1]
    length = math.hypot(dx, dy)
    normal = (-dy/length, dx/length)
    forward = ((head[0]-shoulder[0])*normal[0]
               + (head[1]-shoulder[1])*normal[1])
    if forward < .8:
        head = (head[0] + normal[0]*(.8-forward),
                head[1] + normal[1]*(.8-forward))
    return dict(zip(JOINTS, (hip, shoulder, head, *far_arm, *near_arm,
                            *far_leg, *near_leg)))


# One half-stride: contact, compression, passing, toe-off, drive, extension.
# During stance the planted foot travels backwards relative to the moving hip.
_HALF_RUN = [
    _joints((0, -22.5), (4.0, -35.8), (6.3, -43.3),
            ((11.0, -28.5), (14.8, -34.0)),
            ((-4.5, -29.0), (-.7, -25.4)),
            ((-9.0, -15.5), (-15.0, -8.0)),
            ((8.0, -13.0), (12.0, 0))),
    _joints((0, -21.0), (4.2, -34.3), (6.5, -41.8),
            ((9.3, -26.9), (13.5, -32.0)),
            ((-3.5, -27.4), (-.2, -23.7)),
            ((-3.7, -16.3), (-14.0, -15.0)),
            ((7.3, -10.7), (6.0, 0))),
    _joints((0, -22.2), (4.0, -35.5), (6.3, -43.0),
            ((5.8, -27.0), (10.7, -29.0)),
            ((-.6, -27.0), (1.5, -22.2)),
            ((3.2, -18.1), (-8.0, -19.8)),
            ((3.7, -10.5), (0, 0))),
    _joints((0, -24.0), (4.0, -37.3), (6.3, -44.8),
            ((.4, -28.7), (3.2, -23.5)),
            ((5.8, -28.8), (10.8, -30.4)),
            ((8.8, -20.9), (-.5, -17.8)),
            ((-2.0, -12.6), (-6.0, -.1))),
    _joints((0, -25.0), (3.8, -38.3), (6.1, -45.8),
            ((-4.0, -30.1), (-.3, -25.9)),
            ((10.4, -30.9), (14.0, -36.0)),
            ((11.0, -18.7), (8.8, -7.0)),
            ((-7.6, -15.1), (-13.0, -5.0))),
    _joints((0, -24.1), (3.8, -37.4), (6.1, -44.9),
            ((-5.0, -30.0), (-1.3, -26.1)),
            ((11.7, -30.4), (15.5, -35.8)),
            ((9.3, -15.6), (13.0, -1.8)),
            ((-9.0, -15.0), (-16.2, -7.0))),
]


def _swap_sides(p):
    out = dict(p)
    for stem in ("elbow", "hand", "knee", "foot"):
        out[f"{stem}-far"] = p[f"{stem}-near"]
        out[f"{stem}-near"] = p[f"{stem}-far"]
    return out


RUN_KEYPOSES = tuple(_HALF_RUN + [_swap_sides(p) for p in _HALF_RUN])


_STAND = _joints((0, -22.0), (.9, -35.6), (2.2, -43.1),
                 ((-4.0, -28.3), (-4.5, -20.5)),
                 ((5.1, -28.2), (5.6, -20.4)),
                 ((-3.8, -10.8), (-5.0, 0)),
                 ((3.1, -10.8), (4.2, 0)))

_CROUCH = _joints((-3.0, -11.1), (4.9, -23.7), (9.0, -30.4),
                  ((-3.0, -18.0), (-11.0, -15.1)),
                  ((10.2, -16.1), (13.4, -8.1)),
                  ((-10.8, -6.3), (-9.0, 0)),
                  ((10.0, -8.1), (8.0, 0)))

_JUMP = _joints((0, -23.0), (3.8, -36.6), (6.0, -44.2),
                ((-6.0, -37.0), (-9.2, -45.0)),
                ((10.0, -41.0), (11.6, -48.0)),
                ((-9.4, -17.2), (-16.0, -21.0)),
                ((11.0, -21.0), (12.0, -8.0)))

_TUCK = _joints((-1.2, -23.3), (4.0, -35.2), (6.5, -42.7),
                ((-4.8, -26.0), (1.6, -20.6)),
                ((11.3, -26.8), (8.0, -20.0)),
                ((-4.6, -31.0), (-12.0, -23.0)),
                ((10.0, -29.2), (13.3, -17.0)))

_BREATHE = _joints((0, -20.5), (6.0, -31.3), (9.0, -38.4),
                   ((-1.0, -22.4), (-3.0, -13.3)),
                   ((10.0, -22.0), (5.8, -12.9)),
                   ((-4.4, -10.4), (-5.7, 0)),
                   ((5.0, -10.5), (6.0, 0)))


def blend(a, b, amount):
    """Linear blend of two joint maps, useful for takeoff and landing."""
    amount = max(0.0, min(1.0, amount))
    return {name: tuple(x + (y - x) * amount for x, y in zip(a[name], b[name]))
            for name in JOINTS}


def _catmull(a, b, c, d, t):
    return .5 * (2*b + (-a+c)*t + (2*a-5*b+4*c-d)*t*t
                 + (-a+3*b-3*c+d)*t*t*t)


def _running(phase):
    phase = (phase % 1.0) * len(RUN_KEYPOSES)
    index, t = int(phase), phase % 1
    n = len(RUN_KEYPOSES)
    out = {}
    for name in JOINTS:
        values = [RUN_KEYPOSES[(index + delta) % n][name]
                  for delta in (-1, 0, 1, 2)]
        out[name] = tuple(_catmull(*(q[axis] for q in values), t)
                          for axis in (0, 1))
    # Clamp interpolation at the contact plane and retain constant stance speed.
    for side in ("far", "near"):
        key = f"foot-{side}"
        x, y = out[key]
        out[key] = (x, min(0.0, y))
    return out


def pose(action, phase=0.0, direction=1):
    """Return a pose. Actions: run, stand, crouch, jump, tuck, breathe.

    Run phase is one stride. Breath phase is one inhale/exhale, with phase=0
    and phase=1 at rest. ``direction=-1`` mirrors every joint for left travel.
    Jump/tuck/crouch are fixed keyposes, intended to be blended by the caller.
    """
    if action == "run":
        p = _running(phase)
    elif action == "breathe":
        amount = math.sin(math.pi * (phase % 1.0)) ** 2
        p = dict(_BREATHE)
        for name in ("shoulder", "head"):
            x, y = p[name]
            p[name] = (x - .65 * amount, y - 1.3 * amount)
        for name in ("elbow-far", "elbow-near"):
            x, y = p[name]
            p[name] = (x, y - .55 * amount)
    else:
        templates = {"stand": _STAND, "crouch": _CROUCH,
                     "jump": _JUMP, "tuck": _TUCK}
        if action not in templates:
            raise ValueError(f"Unknown character action: {action}")
        p = dict(templates[action])
    facing = 1 if direction >= 0 else -1
    return {name: (x*facing, y) for name, (x, y) in p.items()}


def _add(a, b):
    return a[0]+b[0], a[1]+b[1]


def _sub(a, b):
    return a[0]-b[0], a[1]-b[1]


def _mul(a, scale):
    return a[0]*scale, a[1]*scale


def _unit(a):
    length = max(.001, math.hypot(*a))
    return a[0]/length, a[1]/length


def _normal(a):
    return -a[1], a[0]


def _point(a):
    return f"{a[0]:.2f} {a[1]:.2f}"


def _polygon(points):
    return "M" + " L".join(_point(p) for p in points) + " Z"


def _chain(a, b, c, widths):
    """A single filled, tapered limb with a rounded wrist/ankle cap."""
    ab, bc = _unit(_sub(b, a)), _unit(_sub(c, b))
    na, nc = _normal(ab), _normal(bc)
    nb = _unit(_add(na, nc))
    sides = []
    for sign in (1, -1):
        sides.append([_add(p, _mul(n, w*sign))
                      for p, n, w in zip((a, b, c), (na, nb, nc), widths)])
    left, right = sides
    return (f"M{_point(left[0])} L{_point(left[1])} L{_point(left[2])} "
            f"Q{_point(_add(c, _mul(bc, widths[2])))} {_point(right[2])} "
            f"L{_point(right[1])} L{_point(right[0])} "
            f"Q{_point(_sub(a, _mul(ab, widths[0])))} {_point(left[0])} Z")


def _capsule(a, b, wa, wb):
    axis = _unit(_sub(b, a))
    n = _normal(axis)
    a1, a2 = _add(a, _mul(n, wa)), _sub(a, _mul(n, wa))
    b1, b2 = _add(b, _mul(n, wb)), _sub(b, _mul(n, wb))
    return (f"M{_point(a1)} L{_point(b1)} "
            f"Q{_point(_add(b, _mul(axis, wb)))} {_point(b2)} "
            f"L{_point(a2)} Q{_point(_sub(a, _mul(axis, wa)))} {_point(a1)} Z")


def _basis(p):
    up = _unit(_sub(p["shoulder"], p["hip"]))
    right = _normal(up)
    neck = _sub(p["head"], p["shoulder"])
    facing = 1 if neck[0]*right[0] + neck[1]*right[1] >= 0 else -1
    return up, _mul(right, facing)


def _local(origin, front, up, x, y):
    # Local y is up, unlike global SVG coordinates.
    return _add(origin, _add(_mul(front, x), _mul(up, y)))


def parts(p):
    """Return stable ``{name, tag, attrs}`` SVG parts in paint order.

    Every part is a path. Number/order of commands stays identical across all
    poses, including mirrored ones, so interpolate ``attrs['d']`` directly.
    The feet are compact trainers, the hood has a small dark visor, and limbs
    are filled silhouettes rather than strokes. No filters or raster assets.
    """
    up, front = _basis(p)
    shape = []

    def add(name, d, fill=WHITE, **attrs):
        shape.append({"name": name, "tag": "path",
                      "attrs": {"d": d, "fill": fill, **attrs}})

    def at(origin, x, y):
        return _local(origin, front, up, x, y)

    def shoe(side, fill):
        foot, knee = p[f"foot-{side}"], p[f"knee-{side}"]
        shin = _sub(knee, foot)
        behind = shin[0]*front[0] + shin[1]*front[1]
        angle = math.radians(max(-14, min(24, behind * 1.3)))
        grounded = abs(foot[1]) < .2 and up[1] < -.7
        if grounded:
            angle = 0
        ca, sa = math.cos(angle), math.sin(angle)
        fx = _add(_mul(front, ca), _mul(up, -sa))
        fy = _add(_mul(up, ca), _mul(front, sa))
        outline = [(-3.4, 4.2), (.5, 4.7), (2.8, 2.0), (6.0, 1.2),
                   (6.8, .1), (6.2, -1.0), (-3.7, -1.0), (-4.1, .5)]
        points = [_local(foot, fx, fy, x, y) for x, y in outline]
        # The sole defines the floor contact. No penetration in a planted frame.
        if grounded:
            shift = max(y for _, y in points) - foot[1]
            points = [(x, y-shift) for x, y in points]
        else:
            shift = 0
        add(f"{side}-shoe", _polygon(points), fill)
        sole = [(-3.6, -.05), (6.5, -.05), (6.2, -1.0), (-3.7, -1.0)]
        solepoints = [_local(foot, fx, fy, x, y) for x, y in sole]
        solepoints = [(x, y-shift) for x, y in solepoints]
        add(f"{side}-sole", _polygon(solepoints), SHADOW)

    # Far side is cool grey so simultaneous limbs remain readable at small size.
    add("far-arm", _chain(p["shoulder"], p["elbow-far"], p["hand-far"],
                          (2.9, 2.5, 1.8)), FAR)
    add("far-glove", _capsule(p["hand-far"],
                              _add(p["hand-far"], _mul(_unit(_sub(p["hand-far"], p["elbow-far"])), 1.1)),
                              2.1, 1.9), FAR)
    add("far-leg", _chain(p["hip"], p["knee-far"], at(p["foot-far"], 0, 2.7),
                          (3.9, 3.0, 2.1)), FAR)
    shoe("far", FAR)
    add("near-leg", _chain(p["hip"], p["knee-near"], at(p["foot-near"], 0, 2.7),
                           (4.0, 3.1, 2.2)))
    shoe("near", WHITE)

    shoulder, hip = p["shoulder"], p["hip"]
    torso = (f"M{_point(at(shoulder, -4.1, .8))} "
             f"Q{_point(at(shoulder, 0, 2.4))} {_point(at(shoulder, 4.8, .1))} "
             f"L{_point(at(hip, 4.0, -.6))} "
             f"Q{_point(at(hip, .5, -3.4))} {_point(at(hip, -4.0, -1.4))} "
             f"L{_point(at(shoulder, -4.1, .8))} Z")
    add("torso", torso)
    add("waist", _polygon([at(hip, -3.8, .6), at(hip, 3.9, .7),
                           at(hip, 3.9, -.4), at(hip, -3.7, -.7)]), INK,
        opacity=".42")
    add("neck", _capsule(shoulder, at(p["head"], 0, -3.0), 2.4, 2.4))

    # Angular hood/helmet profile and a single dark visor give the figure a
    # recognizable game sprite identity without tiny decoration.
    head = p["head"]
    hood = (f"M{_point(at(head, -3.8, -3.2))} "
            f"Q{_point(at(head, -5.7, 1.2))} {_point(at(head, -3.1, 4.3))} "
            f"Q{_point(at(head, .5, 6.0))} {_point(at(head, 3.5, 3.5))} "
            f"L{_point(at(head, 4.2, 1.0))} L{_point(at(head, 5.0, -.3))} "
            f"L{_point(at(head, 3.7, -1.0))} L{_point(at(head, 3.0, -3.6))} "
            f"Q{_point(at(head, -.7, -4.7))} {_point(at(head, -3.8, -3.2))} Z")
    add("hood", hood)
    add("visor", _polygon([at(head, .8, 1.7), at(head, 3.8, 1.2),
                           at(head, 4.0, -.1), at(head, .6, .3)]), INK)
    add("hood-seam", _polygon([at(head, -3.5, -2.6), at(head, -1.9, -3.4),
                               at(head, -1.4, -2.8), at(head, -3.0, -2.0)]), SHADOW)

    add("near-arm", _chain(shoulder, p["elbow-near"], p["hand-near"],
                           (3.1, 2.6, 1.8)))
    add("near-glove", _capsule(p["hand-near"],
                               _add(p["hand-near"], _mul(_unit(_sub(p["hand-near"], p["elbow-near"])), 1.3)),
                               2.25, 2.1))
    # A narrow wrist cuff makes the forearm, glove and elbow read as a filled
    # athletic character rather than a line figure.
    hand, elbow = p["hand-near"], p["elbow-near"]
    arm_axis = _unit(_sub(hand, elbow))
    wrist = _sub(hand, _mul(arm_axis, 1.2))
    add("wrist-cuff", _capsule(_sub(wrist, _mul(arm_axis, .55)),
                               _add(wrist, _mul(arm_axis, .55)), 2.0, 2.0), INK,
        opacity=".50")
    return shape


if __name__ == "__main__":
    from pathlib import Path
    from xml.etree.ElementTree import Element, SubElement, tostring
    target = Path(__file__).with_name("character-sheet.svg")
    svg = Element("svg", xmlns="http://www.w3.org/2000/svg",
                  viewBox="0 0 1000 340", width="1000", height="340")
    SubElement(svg, "rect", width="1000", height="340", fill="#0d1117")
    for index in range(12):
        x, y = 54 + (index % 6)*166, 114 + (index//6)*108
        group = SubElement(svg, "g", transform=f"translate({x} {y}) scale(1.6)")
        SubElement(group, "path", d="M-24 0H30", stroke="#243c3d")
        for item in parts(pose("run", index/12)):
            SubElement(group, item["tag"], item["attrs"])
        label = SubElement(svg, "text", x=str(x), y=str(y+26), fill="#93b3ae",
                           **{"font-size": "11", "font-family": "monospace",
                              "text-anchor": "middle"})
        label.text = f"RUN {index:02d}"
    for index, action in enumerate(("stand", "crouch", "jump", "tuck", "breathe")):
        group = SubElement(svg, "g", transform=f"translate({82+index*196} 315)")
        for item in parts(pose(action, .5)):
            SubElement(group, item["tag"], item["attrs"])
        label = SubElement(svg, "text", x=str(82+index*196), y="338", fill="#93b3ae",
                           **{"font-size": "11", "font-family": "monospace",
                              "text-anchor": "middle"})
        label.text = action.upper()
    target.write_bytes(tostring(svg))
    print(target)
