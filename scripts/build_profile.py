"""Build responsive vector profiles and their paragraph-by-paragraph runner."""
from pathlib import Path
import argparse
import html
import math
import re
import xml.etree.ElementTree as ET
from PIL import ImageFont
from profile_content import load_profile
import runner

ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def tag(name):
    return f"{{{NS}}}{name}"


def add(parent, name, **attrs):
    return ET.SubElement(parent, tag(name), {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def clean(text):
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    return html.unescape(text.replace("**", "").replace("`", "").removeprefix("- ").replace("&nbsp;", " "))


def font(size, bold=False):
    candidates = [
        f"/System/Library/Fonts/Supplemental/Arial{' Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation2/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.truetype("DejaVuSans.ttf", size)


def wrapped(text, size, width, bold=False):
    f = font(size, bold)
    lines, line = [], ""
    for word in clean(text).split():
        candidate = f"{line} {word}".strip()
        if line and f.getlength(candidate) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + ([line] if line else [])


class Layout:
    def __init__(self, width):
        self.width = width
        self.mobile = width < 1000
        self.margin = 32 if self.mobile else 76
        self.body_size = 28
        self.platforms = []
        self.svg = ET.Element(tag("svg"), {
            "width": str(width), "role": "img", "aria-labelledby": "profile-title profile-desc",
        })
        add(self.svg, "title", id="profile-title").text = "SK Arin: ML systems, projects, and a vector parkour journey"
        add(self.svg, "desc", id="profile-desc").text = (
            "A complete illustrated profile. A white hooded platformer athlete runs and jumps "
            "from the name through every paragraph, ending at A little beyond the code. "
            "The runner takes three breaths and stands still. A selectable transcript and "
            "clickable project links follow this image. Reduced motion shows the final pose."
        )
        self.background = add(self.svg, "rect", width=width, height="100%", fill="#0D1117")
        self.content = add(self.svg, "g", font_family="Arial, Helvetica, sans-serif")
        self.cursor = 330 if self.mobile else 400
        self.header()

    def text(self, text, x, y, size=28, color="#C9D1D9", bold=False):
        node = add(self.content, "text", x=f"{x:.2f}", y=f"{y:.2f}", font_size=size,
                   fill=color, font_weight="700" if bold else "400")
        node.text = clean(text)
        return font(size, bold).getlength(clean(text))

    def paragraph(self, text, x=None, y=None, width=None, size=28, color="#C9D1D9", bold=False,
                  direction=None, visit=True, all_lines=False):
        x = self.margin if x is None else x
        y = self.cursor if y is None else y
        width = self.width - 2 * self.margin if width is None else width
        lines = wrapped(text, size, width, bold)
        leading = size * (2.72 if all_lines else 1.43)
        for i, line in enumerate(lines):
            baseline = y + i * leading
            measured = self.text(line, x, baseline, size, color, bold)
            if visit and (i == 0 or all_lines):
                self.platforms.append({"x": x, "y": baseline - size * .75 - 2,
                                       "width": measured, "direction": direction if not all_lines else (1 if (len(lines)-i) % 2 else -1),
                                       "label": clean(text)[:65]})
        last = y + max(0, len(lines)-1) * leading
        self.cursor = last + 84
        return last

    def heading(self, text):
        self.cursor += 20
        self.paragraph(text, size=38 if self.mobile else 42, color="#F0F3F6", bold=True, visit=False)
        add(self.content, "path", d=f"M{self.margin} {self.cursor-58}H{self.width-self.margin}",
            stroke="#293640", stroke_width="1")

    def header(self):
        original = ET.parse(ROOT / "assets/hero.svg").getroot()
        if not self.mobile:
            original.set("x", "0")
            original.set("y", "0")
            self.svg.append(original)
            return
        defs = original.find(tag("defs"))
        self.svg.append(defs)
        add(self.content, "rect", width=640, height=330, rx=12, fill="url(#bg)", stroke="#2A373D")
        add(self.content, "rect", width=640, height=330, fill="url(#glow)")
        self.text("@ska2704 / KOLKATA, INDIA", 32, 37, 9, "#ABC5C3")
        self.text("SK ARIN", 32, 143, 64, "#F2F1E9", True)
        self.text("Machine learning. Real-world systems.", 32, 204, 19, "#B6CAC9")
        add(self.content, "path", d="M32 245H608", stroke="#26383B")
        for value, x, color in [("COMPETITIVE ML",32,"#A4F6D3"),("OPEN SOURCE",159,"#C1CFCD"),("BUILDING IN PUBLIC",368,"#C1CFCD")]:
            self.text(value, x, 290, 9, color, True)
        for group in original.findall(tag("g")):
            if group.get("class") in {"still-art", "motion-art"}:
                group.set("transform", "translate(-65 20) scale(.55)")
                self.svg.append(group)

    def build(self, data):
        self.cursor += 86
        identity = "AI/ML contributor & benchmark author · Kaggle Notebook Expert · CSE (AI & ML)"
        self.paragraph(identity, size=24 if not self.mobile else 26, color="#E6EDF3", bold=True, direction=-1)
        self.cursor -= 5
        self.paragraph("KAGGLE / skarin · GITHUB / ska2704 · LINKEDIN / SK ARIN", size=18 if not self.mobile else 20,
                       color="#A4F6D3", visit=False)
        for i, paragraph in enumerate(data["intro"]):
            self.paragraph(paragraph, direction=1 if i == 0 else -1)
        self.heading("Selected builds")
        if self.mobile:
            for project in data["projects"]:
                self.project(project, self.margin, self.cursor, self.width-2*self.margin)
        else:
            card_width = (self.width-2*self.margin-28)/2
            for row, pair in enumerate([data["projects"][:2], data["projects"][2:]]):
                top = self.cursor
                heights, platforms = [], []
                for i, project in enumerate(pair):
                    before = len(self.platforms)
                    heights.append(self.project(project, self.margin+i*(card_width+28), top, card_width))
                    platforms.append(self.platforms.pop(before))
                # Travel across each row, then reverse through the next row.
                if row == 1:
                    for platform in reversed(platforms):
                        platform["direction"] = -1
                        self.platforms.append(platform)
                else:
                    for platform in platforms:
                        platform["direction"] = 1
                        self.platforms.append(platform)
                self.cursor = top + max(heights) + 70
        for section in data["sections"]:
            self.heading(section["heading"])
            for paragraph in section["paragraphs"]:
                if section["heading"] == "Tools I reach for" and "`" in paragraph:
                    label = re.match(r"\*\*(.*?)\*\*",paragraph).group(1)
                    paragraph = label+": "+" · ".join(re.findall(r"`([^`]+)`",paragraph))
                self.paragraph(paragraph)
        self.heading(data["beyond"]["heading"])
        self.paragraph(data["beyond"]["text"], all_lines=True)
        self.cursor += 10
        add(self.content, "path", d=f"M{self.margin} {self.cursor-40}H{self.width-self.margin}", stroke="#293640")
        self.paragraph(data["footer"], size=21, color="#8BA4A8", visit=False)
        self.height = math.ceil(self.cursor + 20)
        self.svg.set("height", str(self.height))
        self.svg.set("viewBox", f"0 0 {self.width} {self.height}")
        self.background.set("height", str(self.height))

    def project(self, project, x, y, width):
        padding = 26
        size = 26 if not self.mobile else 28
        description = wrapped(project["description"], size, width-2*padding)
        height = 228 + len(description) * size * 1.43
        add(self.content, "rect", x=x, y=y-35, width=width, height=height, rx=12,
            fill="#101820", stroke="#273641", stroke_width="1.3")
        self.text(project["label"], x+padding, y, 17, "#83B9B4", True)
        self.text(project["title"], x+padding, y+60, 34, "#EDF5F2", True)
        self.paragraph(project["description"], x=x+padding, y=y+151, width=width-2*padding, size=size,
                       direction=1, visit=True)
        tool_y = y+height-64
        self.paragraph(" · ".join(project["tools"]), x=x+padding, y=tool_y, width=width-2*padding,
                       size=18, color="#8FAEAD", visit=False)
        self.cursor = y+height+65
        return height


class Journey:
    def __init__(self, layout):
        self.layout = layout
        self.segments = []
        self.time = 0.0
        self.current = (40, 97) if layout.mobile else (82, 118)
        self.scale = .65 if layout.mobile else .67

    def move(self, kind, x, y, duration, scale=None, arc=0, direction=None, label=""):
        scale = self.scale if scale is None else scale
        xa, ya = self.current
        direction = (1 if x >= xa else -1) if direction is None else direction
        self.segments.append({"start": self.time, "end": self.time+duration, "kind": kind,
                              "a": self.current, "b": (x,y), "sa": self.scale, "sb": scale,
                              "arc": arc, "direction": direction, "label": label})
        self.time += duration
        self.current, self.scale = (x,y), scale

    def header(self):
        if self.layout.mobile:
            route = [("ready",40,97,.4,0),("run",121,97,1.3,0),("jump",158,97,.6,12),
                     ("run",296,97,1.6,0),("flip",349,190,.9,18),("land",349,190,.2,0),
                     ("run",40,190,3.6,0),("drop",40,245,.8,8),("jump",40,283,.7,12),
                     ("run",118,283,1,0),("jump",165,283,.7,17),("run",231,283,.8,0),
                     ("flip",373,283,1,23),("run",481,283,1.25,0)]
        else:
            route = [("ready",82,118,.4,0),("run",150,118,1,0),("jump",175,118,.5,16),
                     ("run",180,118,.25,0),("jump",232,118,.7,18),("run",392,118,2.35,0),
                     ("flip",477,208,1.05,29),("land",477,208,.25,0),("run",410,208,.9,0),
                     ("jump",374,204,.6,16),("run",283,204,1.1,0),("jump",246,208,.55,16),
                     ("run",160,208,.85,0),("jump",125,204,.5,14),("run",86,204,.5,0),
                     ("drop",91,274,.9,10),("jump",96,315,.7,18),("run",180,315,1.15,0),
                     ("flip",270,315,1,29),("run",335,315,.85,0),("jump",435,315,1,28),
                     ("run",560,315,1.35,0)]
        for kind,x,y,duration,arc in route:
            self.move(kind,x,y,duration,arc=arc,label="Banner lettering")
        self.hero_end = self.time

    def connect(self, x, y, scale=1):
        px, py = self.current
        distance = abs(x-px)
        if abs(y-py) < 12:
            self.move("jump",x,y,max(.55,distance/250),scale=scale,arc=24)
            return
        side = -1 if px < self.layout.width/2 else 1
        clearance = 22 if self.layout.mobile else 24
        gutter = clearance if side < 0 else self.layout.width-clearance
        # Exit the paragraph horizontally, descend outside its letters, then land.
        self.move("jump",gutter,py,.45,scale=scale,arc=18)
        self.move("fall",gutter,y-14,max(.4,math.sqrt(abs(y-py)/650)),scale=scale)
        self.move("jump",x,y,max(.35,abs(x-gutter)/260),scale=scale,arc=10)
        self.move("land",x,y,.16,scale=scale)

    def build(self):
        self.header()
        for i, platform in enumerate(self.layout.platforms):
            left, right = platform["x"]+10, platform["x"]+max(18,platform["width"]-10)
            direction = platform["direction"] or (1 if abs(self.current[0]-left)<abs(self.current[0]-right) else -1)
            start, end = (left,right) if direction > 0 else (right,left)
            if i == 0:
                # The banner ends over the middle of the first paragraph.
                middle = min(right,max(left,self.current[0]))
                self.move("jump",middle,platform["y"],.9,scale=.86 if self.layout.mobile else 1,arc=18)
                self.move("run",right,platform["y"],max(.25,abs(right-middle)/260),direction=1,label=platform["label"])
                start, end, direction = right, left, -1
            else:
                if abs(start-self.current[0]) > self.layout.width*.65:
                    self.move("run",start,self.current[1],abs(start-self.current[0])/260,
                              label="Turn and cross the current paragraph")
                self.connect(start,platform["y"],.86 if self.layout.mobile else 1)
            self.move("run",end,platform["y"],max(.35,abs(end-start)/260),direction=direction,label=platform["label"])
        x,y = self.current
        self.move("brake",x,y,.45,direction=1)
        self.move("breathe",x,y,4.5,direction=1)
        self.move("stand",x,y,.8,direction=1)
        self.duration = self.time

    def frame(self, time):
        s = next((s for s in self.segments if s["start"] <= time < s["end"]), self.segments[-1])
        u = min(1,max(0,(time-s["start"])/(s["end"]-s["start"])))
        xa,ya = s["a"]; xb,yb = s["b"]
        x = xa+(xb-xa)*u
        y = ya+(yb-ya)*(u*u if s["kind"] == "fall" else u)
        scale = s["sa"]+(s["sb"]-s["sa"])*u
        kind = s["kind"]
        phase = time/((.55 if self.layout.mobile else .68) if s["start"] < self.hero_end else (.24 if self.layout.mobile else .28))
        p = runner.pose("run",phase)
        if kind in {"jump","flip","drop","fall"}:
            y -= s["arc"]*4*u*(1-u)
            if kind == "drop":
                x -= (24 if self.layout.mobile else 32)*math.sin(math.pi*u)
            p = runner.blend(p,runner.pose("jump"),min(1,u*6))
            if kind == "flip":
                p = runner.blend(p,runner.pose("tuck"),math.sin(math.pi*u)**2)
                angle = math.pi*2*(u*u*(3-2*u))
                c, sn = math.cos(angle),math.sin(angle)
                p = {k:(cx*c-(cy+23)*sn,cx*sn+(cy+23)*c-23) for k,(cx,cy) in p.items()}
            p = runner.blend(p,runner.pose("crouch"),max(0,(u-.82)/.18))
        elif kind in {"ready","brake"}:
            p = runner.blend(runner.pose("stand"),runner.pose("crouch"),u)
        elif kind == "land":
            p = runner.blend(runner.pose("crouch"),runner.pose("run",phase),u)
        elif kind == "breathe":
            p = runner.pose("breathe",u*3)
            p = runner.blend(runner.pose("crouch"),p,min(1,u*18))
        elif kind == "stand":
            p = runner.blend(runner.pose("breathe",0),runner.pose("stand"),u*u*(3-2*u))
        return x,y,scale,s["direction"],kind,p


def animate(parent, attribute, values, times, duration, discrete=False):
    add(parent,"animate",attributeName=attribute,values=";".join(values),
        keyTimes=";".join(f"{t/duration:.7f}" for t in times),dur=f"{duration:.4f}s",
        repeatCount="1",fill="freeze",calcMode="discrete" if discrete else "linear")


def transform(parent, kind, values, times, duration, discrete=False):
    add(parent,"animateTransform",attributeName="transform",type=kind,values=";".join(values),
        keyTimes=";".join(f"{t/duration:.7f}" for t in times),dur=f"{duration:.4f}s",
        repeatCount="1",fill="freeze",calcMode="discrete" if discrete else "linear")


def append_character(layout, journey):
    defs = add(layout.svg,"defs")
    add(defs,"style").text = """
      .journey-motion{display:none}
      @media(prefers-reduced-motion:no-preference){.journey-motion{display:inline}.journey-still{display:none}}
    """
    times = {0, journey.duration}
    display_times = {0,journey.duration}
    for s in journey.segments:
        count = 1 if s["kind"] == "run" else max(1,math.ceil((s["end"]-s["start"])*18))
        times.update(s["start"]+(s["end"]-s["start"])*i/count for i in range(count+1))
        display_times.update([s["start"],s["end"]])
    times,display_times = sorted(times),sorted(display_times)
    frames = [journey.frame(t) for t in times]
    group = add(layout.svg,"g",id="journey-runner",**{"class":"journey-motion","aria-hidden":"true"})
    transform(group,"translate",[f"{x:.2f} {y:.2f}" for x,y,*_ in frames],times,journey.duration)
    scaled = add(group,"g")
    transform(scaled,"scale",[f"{s:.4f}" for _,_,s,*_ in frames],times,journey.duration)
    facing = add(scaled,"g")
    transform(facing,"scale",[f"{journey.frame(t)[3]} 1" for t in display_times],display_times,journey.duration,True)
    for hero in [True,False]:
        gait = add(facing,"g",id="runner-gait-header" if hero else "runner-gait-body")
        visible = []
        for t in display_times:
            kind = journey.frame(t)[4]
            visible.append("inline" if kind=="run" and (t<journey.hero_end)==hero else "none")
        animate(gait,"display",visible,display_times,journey.duration,True)
        poses = [runner.parts(runner.pose("run",i/24)) for i in range(25)]
        for index, part in enumerate(poses[0]):
            node = add(gait,part["tag"],**part["attrs"])
            add(node,"animate",attributeName="d",values=";".join(p[index]["attrs"]["d"] for p in poses),
                dur=(".55s" if layout.mobile else ".68s") if hero else (".24s" if layout.mobile else ".28s"),
                repeatCount="indefinite",end=f"{journey.duration:.4f}s")
    action = add(facing,"g",id="runner-actions")
    animate(action,"display",["none" if journey.frame(t)[4]=="run" else "inline" for t in display_times],
            display_times,journey.duration,True)
    all_parts = [runner.parts(f[-1]) for f in frames]
    for i, part in enumerate(all_parts[0]):
        node = add(action,part["tag"],**part["attrs"])
        animate(node,"d",[p[i]["attrs"]["d"] for p in all_parts],times,journey.duration)
    x,y,scale,_,_,p = journey.frame(journey.duration)
    still = add(layout.svg,"g",transform=f"translate({x:.2f} {y:.2f}) scale({scale:.4f})",
                **{"class":"journey-still","aria-hidden":"true"})
    for part in runner.parts(p):
        add(still,part["tag"],**part["attrs"])


def build(width):
    data = load_profile(ROOT/"content/profile.md")
    layout = Layout(width)
    layout.build(data)
    journey = Journey(layout)
    journey.build()
    append_character(layout,journey)
    ET.indent(layout.svg,space="  ")
    name = "profile-mobile" if layout.mobile else "profile-desktop"
    asset = ROOT/f"assets/{name}.svg"
    asset.write_text(ET.tostring(layout.svg,encoding="unicode")+"\n")
    return {"name":name,"width":width,"height":layout.height,"duration":journey.duration,
            "bytes":asset.stat().st_size,"platforms":layout.platforms,"segments":journey.segments}


def write_readme(ref):
    base = f"https://raw.githubusercontent.com/ska2704/ska2704/{ref}/assets"
    transcript = (ROOT/"content/profile.md").read_text()
    prefix = f'''<picture>
  <source media="(max-width: 700px)" srcset="{base}/profile-mobile.svg" />
  <img src="{base}/profile-desktop.svg" alt="SK Arin's full profile. A white vector game character parkours through the paragraphs to A little beyond the code, catches its breath, and stands still." width="100%" />
</picture>

<p align="center">
  <a href="https://www.kaggle.com/skarin"><img src="assets/kaggle.svg" alt="Kaggle: skarin" height="38" /></a>
  &nbsp;
  <a href="https://github.com/ska2704?tab=repositories"><img src="assets/projects.svg" alt="Explore projects" height="38" /></a>
  &nbsp;
  <a href="https://www.linkedin.com/in/sk-arin/"><img src="assets/linkedin.svg" alt="LinkedIn: SK Arin" height="38" /></a>
</p>

<p align="center">
  <a href="https://github.com/ska2704/PitWall">PitWall</a> ·
  <a href="https://github.com/ska2704/podmind">PodMind</a> ·
  <a href="https://github.com/ska2704/hybridtox">HybridTox</a> ·
  <a href="https://github.com/ska2704/axiom">Axiom</a>
</p>

<details>
<summary><b>Read the profile text and project details</b></summary>

'''
    (ROOT/"README.md").write_text(prefix+transcript+"\n</details>\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-readme",action="store_true")
    parser.add_argument("--ref",default="main")
    args = parser.parse_args()
    import json
    builds = [build(1280),build(640)]
    (ROOT/"content/journey.json").write_text(json.dumps(builds,indent=2)+"\n")
    if args.write_readme:
        write_readme(args.ref)
    for result in builds:
        print({k:result[k] for k in ["name","width","height","duration","bytes"]})
