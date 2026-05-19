import adsk.core, adsk.fusion, traceback
import os, csv, math, json

app = None
ui  = None
handlers = []

# --- Persistence Logic ---
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'picket_planter_settings.json')

def load_settings():
    """Load settings from JSON, ensuring all values are treated as strings for ValueInput compatibility."""
    defaults = {
        'ext_length': '14.0 in', 'ext_width': '12.75 in', 'target_height': '16.5 in',
        'leg_elevation': '4.0 in', 'picket_width': '5.5 in', 'picket_thick': '0.625 in',
        'leg_wide': '1.75 in', 'leg_narrow': '1.125 in', 'rim_overhang': '0.25 in',
        'rim_width': '1.75 in', 'cleat_width': '0.5 in', 'cleat_inset': '0.25 in',
        'stock_length': '96.0 in', 'kerf': '0.125 in', 'cost': '3.50'
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
                for k, v in saved.items():
                    defaults[k] = str(v) # Force to string
        except: pass
    return defaults

def save_settings(inputs):
    """Save all current input expressions to JSON."""
    settings = {}
    ids = ['ext_length', 'ext_width', 'target_height', 'leg_elevation', 'picket_width', 'picket_thick', 
           'leg_wide', 'leg_narrow', 'rim_overhang', 'rim_width', 'cleat_width', 'cleat_inset',
           'stock_length', 'kerf', 'cost']
    for pid in ids:
        cmd_input = inputs.itemById(pid)
        if cmd_input:
            settings[pid] = cmd_input.expression if hasattr(cmd_input, 'expression') else str(cmd_input.value)
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
    except: pass

# --- Geometry Helpers ---
def draw_rect(sketches, plane, x1, y1, x2, y2):
    sketch = sketches.add(plane)
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(x1, y1, 0), adsk.core.Point3D.create(x2, y2, 0))
    return sketch

def draw_poly(sketches, plane, points):
    sketch = sketches.add(plane)
    lines = sketch.sketchCurves.sketchLines
    for i in range(len(points)):
        p1, p2 = points[i], points[(i+1)%len(points)]
        lines.addByTwoPoints(adsk.core.Point3D.create(p1[0], p1[1], 0), adsk.core.Point3D.create(p2[0], p2[1], 0))
    return sketch

def extrude_simple(comp, sketch, dist):
    objs = adsk.core.ObjectCollection.create()
    for prof in sketch.profiles: objs.add(prof)
    ext_input = comp.features.extrudeFeatures.createInput(objs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(dist))
    return comp.features.extrudeFeatures.add(ext_input)

def build_model(inputs):
    """Generates the 3D model geometry based on current inputs."""
    design = adsk.fusion.Design.cast(app.activeProduct)
    rootComp = design.rootComponent
    
    try:
        L = inputs.itemById('ext_length').value
        W = inputs.itemById('ext_width').value
        H_t = inputs.itemById('target_height').value
        Elev = inputs.itemById('leg_elevation').value
        PW = inputs.itemById('picket_width').value
        PT = inputs.itemById('picket_thick').value
        LW = inputs.itemById('leg_wide').value
        LN = inputs.itemById('leg_narrow').value
        O = inputs.itemById('rim_overhang').value
        RW = inputs.itemById('rim_width').value
        CW = inputs.itemById('cleat_width').value
        CI = inputs.itemById('cleat_inset').value
        if PW < 0.1: return None
    except: return None

    # Snapping wall height to board multiples
    count = max(1, round(H_t / PW))
    wall_h = count * PW
    leg_h = wall_h + Elev

    # Clean previous iterations
    occ = rootComp.occurrences.itemByName("Picket Planter")
    if occ: occ.deleteMe()
    
    mainOcc = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    mainOcc.component.name = "Picket Planter"
    pc = mainOcc.component
    
    def sub(name):
        o = pc.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        o.component.name = name; return o.component

    c_long, c_short, c_leg, c_floor, c_rim = [sub(n) for n in ["Long Walls", "Short Walls", "Legs", "Floor & Bracing", "Rim Cap"]]
    xy, z_axis = rootComp.xYConstructionPlane, rootComp.zConstructionAxis

    # Legs (Absolute Corners)
    configs = [(0,0,LW,PT,0,PT,PT,LN), (W-LW,0,LW,PT,W-PT,PT,PT,LN), 
               (0,L-PT,LW,PT,0,L-LN,PT,LN), (W-LW,L-PT,LW,PT,W-PT,L-LN,PT,LN)]
    for x1,y1,w1,h1,x2,y2,w2,h2 in configs:
        extrude_simple(c_leg, draw_rect(c_leg.sketches, xy, x1, y1, x1+w1, y1+h1), leg_h)
        extrude_simple(c_leg, draw_rect(c_leg.sketches, xy, x2, y2, x2+w2, y2+h2), leg_h)

    # Walls
    wp_in = pc.constructionPlanes.createInput(); wp_in.setByOffset(xy, adsk.core.ValueInput.createByReal(Elev))
    wp = pc.constructionPlanes.add(wp_in)
    for x in [PT, W-2*PT]:
        sk = draw_rect(c_long.sketches, wp, x, PT, x+PT, L-PT); ex = extrude_simple(c_long, sk, PW)
        if count > 1:
            pat_in = c_long.features.rectangularPatternFeatures.createInput(adsk.core.ObjectCollection.createWithArray(list(ex.bodies)), z_axis, adsk.core.ValueInput.createByReal(count), adsk.core.ValueInput.createByReal(PW), adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
            c_long.features.rectangularPatternFeatures.add(pat_in)
    for y in [PT, L-2*PT]:
        sk = draw_rect(c_short.sketches, wp, 2*PT, y, W-2*PT, y+PT); ex = extrude_simple(c_short, sk, PW)
        if count > 1:
            pat_in = c_short.features.rectangularPatternFeatures.add(c_short.features.rectangularPatternFeatures.createInput(adsk.core.ObjectCollection.createWithArray(list(ex.bodies)), z_axis, adsk.core.ValueInput.createByReal(count), adsk.core.ValueInput.createByReal(PW), adsk.fusion.PatternDistanceType.SpacingPatternDistanceType))

    # Floor & Cleats
    extrude_simple(c_floor, draw_rect(c_floor.sketches, wp, 2*PT, 2*PT+CI, 2*PT+CW, L-2*PT-CI), PT)
    extrude_simple(c_floor, draw_rect(c_floor.sketches, wp, W-2*PT-CW, 2*PT+CI, W-2*PT, L-2*PT-CI), PT)
    
    fp_in = pc.constructionPlanes.createInput(); fp_in.setByOffset(wp, adsk.core.ValueInput.createByReal(PT))
    fp = pc.constructionPlanes.add(fp_in)
    avail_l = L - 4*PT
    num_f = math.floor(avail_l / PW)
    for j in range(num_f):
        sk = draw_rect(c_floor.sketches, fp, 2*PT, 2*PT+j*PW, W-2*PT, 2*PT+(j+1)*PW)
        extrude_simple(c_floor, sk, PT)
    if avail_l % PW > 0.01:
        sk = draw_rect(c_floor.sketches, fp, 2*PT, 2*PT+num_f*PW, W-2*PT, 2*PT+num_f*PW+(avail_l % PW))
        extrude_simple(c_floor, sk, PT)

    # Rim
    rp_in = pc.constructionPlanes.createInput(); rp_in.setByOffset(xy, adsk.core.ValueInput.createByReal(leg_h))
    rp = pc.constructionPlanes.add(rp_in)
    pts = [[(-O,-O), (W+O,-O), (W+O-RW,-O+RW), (-O+RW,-O+RW)], [(-O,L+O), (W+O,L+O), (W+O-RW,L+O-RW), (-O+RW,L+O-RW)],
           [(-O,-O), (-O+RW,-O+RW), (-O+RW,L+O-RW), (-O,L+O)], [(W+O,-O), (W+O-RW,-O+RW), (W+O-RW,L+O-RW), (W+O,L+O)]]
    for p in pts: extrude_simple(c_rim, draw_poly(c_rim.sketches, rp, p), PT)
    return pc

def export_bom(pc, inputs):
    """Calculates cut layout and exports CSV to selected folder."""
    folder_dialog = ui.createFolderDialog(); folder_dialog.title = "Select Folder for BOM"
    if folder_dialog.showDialog() == adsk.core.DialogResults.DialogOK:
        bodies = []
        for occ in pc.allOccurrences:
            for b in occ.component.bRepBodies:
                if not b.isSolid: continue
                bb = b.boundingBox; d = sorted([(bb.maxPoint.x-bb.minPoint.x)/2.54, (bb.maxPoint.y-bb.minPoint.y)/2.54, (bb.maxPoint.z-bb.minPoint.z)/2.54])
                bodies.append({'name': occ.component.name, 'thick': d[0], 'width': d[1], 'length': d[2]})
        
        stock_l = inputs.itemById('stock_length').value / 2.54
        kerf = inputs.itemById('kerf').value / 2.54
        cost = float(inputs.itemById('cost').expression)
        
        # 1D FFD Logic
        groups = {}
        for b in bodies:
            t, w = round(b['thick'], 3), round(b['width'], 3)
            if t > w: t, w = w, t
            key = (t, w)
            if key not in groups: groups[key] = []
            groups[key].append(b)
        
        layout = {}; total_b = 0
        for key, parts in groups.items():
            parts = sorted(parts, key=lambda x: x['length'], reverse=True); bins = []
            for p in parts:
                placed = False
                for i in range(len(bins)):
                    if sum(x['length'] for x in bins[i]) + len(bins[i])*kerf + p['length'] <= stock_l:
                        bins[i].append(p); placed = True; break
                if not placed: bins.append([p])
            layout[key] = bins; total_b += len(bins)
            
        path = os.path.join(folder_dialog.folder, 'planter_bom_and_cutlist.csv')
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['--- PROJECT SUMMARY ---']); w.writerow(['Total Boards:', total_b, 'Cost:', f'${total_b*cost:.2f}'])
            w.writerow([]); w.writerow(['--- BILL OF MATERIALS ---']); w.writerow(['Part', 'Qty', 'T', 'W', 'L'])
            counts = {}
            for b in bodies:
                k = (b['name'], round(b['thick'],3), round(b['width'],3), round(b['length'],3))
                counts[k] = counts.get(k, 0) + 1
            for k, q in sorted(counts.items()): w.writerow([k[0], q, k[1], k[2], f'{k[3]:.2f}'])
            w.writerow([]); w.writerow(['--- CUT LIST ---'])
            for key, bins in layout.items():
                w.writerow([f'Stock: {key[0]}x{key[1]}'])
                for i, bl in enumerate(bins): w.writerow([f' Board #{i+1}', ", ".join([f"{p['name']} ({p['length']:.2f}\")" for p in bl])])
        ui.messageBox(f"BOM exported to: {path}")

# --- UI Handlers ---
class PlanterInputHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            cmd_input = args.input
            if cmd_input.id == 'actions':
                if cmd_input.selectedItem.name == 'UPDATE DRAWING':
                    build_model(args.firingEvent.sender.commandInputs)
                elif cmd_input.selectedItem.name == 'BUILD BOM & CUT LIST':
                    pc = build_model(args.firingEvent.sender.commandInputs)
                    if pc: export_bom(pc, args.firingEvent.sender.commandInputs)
        except: pass

class PlanterExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            build_model(inputs); save_settings(inputs)
        except: ui.messageBox(traceback.format_exc())

class PlanterCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        cmd = args.command
        cmd.isExecutedWhenOk = False # PREVENTS AUTO-UPDATE / CRASHES
        
        onEx = PlanterExecuteHandler(); cmd.execute.add(onEx); handlers.append(onEx)
        onCh = PlanterInputHandler(); cmd.inputChanged.add(onCh); handlers.append(onCh)
        
        inputs = cmd.commandInputs; s = load_settings()
        # Numerical Inputs
        for p, l in [('ext_length','Length'),('ext_width','Width'),('target_height','Tgt H'),('leg_elevation','Elev'),
                     ('picket_width','Picket W'),('picket_thick','Picket T'),('leg_wide','Leg W'),('leg_narrow','Leg N'),
                     ('rim_overhang','Rim Oh'),('rim_width','Rim W'),('cleat_width','Cleat W'),('cleat_inset','Cleat Off'),
                     ('stock_length','Stock L'),('kerf','Saw K')]:
            inputs.addValueInput(p, l, 'in', adsk.core.ValueInput.createByString(s[p]))
        
        inputs.addValueInput('cost', 'Cost/Bd', '', adsk.core.ValueInput.createByString(s['cost']))
        
        # Manual Trigger Button Row (Most reliable UI element for scripts)
        btnRow = inputs.addButtonRowCommandInput('actions', 'Manual Actions', False)
        btnRow.listItems.add('UPDATE DRAWING', False, '')
        btnRow.listItems.add('BUILD BOM & CUT LIST', False, '')

def run(context):
    try:
        global app, ui; app = adsk.core.Application.get(); ui = app.userInterface
        cmdDef = ui.commandDefinitions.itemById('PicketPlanterFinalV8')
        if not cmdDef: cmdDef = ui.commandDefinitions.addButtonDefinition('PicketPlanterFinalV8', 'Picket Planter (Robust)', '')
        onCr = PlanterCreatedHandler(); cmdDef.commandCreated.add(onCr); handlers.append(onCr)
        cmdDef.execute()
        adsk.autoTerminate(False)
    except: ui.messageBox(traceback.format_exc())

def stop(context):
    try:
        cmdDef = ui.commandDefinitions.itemById('PicketPlanterFinalV8')
        if cmdDef: cmdDef.deleteMe()
    except: pass
