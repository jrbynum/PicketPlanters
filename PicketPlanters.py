import adsk.core, adsk.fusion, traceback
import os, csv, math, json

app = None
ui  = None
handlers = []
_needs_update = False # Global flag to trigger preview only on button click

# --- Persistence Logic ---
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'picket_planter_settings.json')

def load_settings():
    default_settings = {
        'ext_length': '14.0 in', 'ext_width': '12.75 in', 'target_height': '16.5 in',
        'leg_elevation': '4.0 in', 'picket_width': '5.5 in', 'picket_thick': '0.625 in',
        'leg_wide': '1.75 in', 'leg_narrow': '1.125 in', 'rim_overhang': '0.25 in',
        'rim_width': '1.75 in', 'cleat_width': '0.5 in', 'cleat_inset': '0.25 in',
        'stock_length': '96.0 in', 'kerf': '0.125 in', 'cost': 3.50
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
                default_settings.update(saved)
        except: pass
    return default_settings

def save_settings(inputs):
    settings = {}
    for pid in ['ext_length', 'ext_width', 'target_height', 'leg_elevation', 'picket_width', 'picket_thick', 
                'leg_wide', 'leg_narrow', 'rim_overhang', 'rim_width', 'cleat_width', 'cleat_inset',
                'stock_length', 'kerf']:
        settings[pid] = inputs.itemById(pid).expression
    settings['cost'] = inputs.itemById('cost').value
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
    except: pass

# --- Geometry Logic ---
def draw_rect(sketches, plane, x1, y1, x2, y2):
    sketch = sketches.add(plane)
    lines = sketch.sketchCurves.sketchLines
    lines.addTwoPointRectangle(adsk.core.Point3D.create(x1, y1, 0), adsk.core.Point3D.create(x2, y2, 0))
    return sketch

def draw_polygon(sketches, plane, points):
    sketch = sketches.add(plane)
    lines = sketch.sketchCurves.sketchLines
    for i in range(len(points)):
        p1, p2 = points[i], points[(i+1)%len(points)]
        lines.addByTwoPoints(adsk.core.Point3D.create(p1[0], p1[1], 0), adsk.core.Point3D.create(p2[0], p2[1], 0))
    return sketch

def extrude_sketch(comp, sketch, distance_str):
    objs = adsk.core.ObjectCollection.create()
    for prof in sketch.profiles: objs.add(prof)
    ext_input = comp.features.extrudeFeatures.createInput(objs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByString(distance_str))
    return comp.features.extrudeFeatures.add(ext_input)

def build_model(inputs):
    design = adsk.fusion.Design.cast(app.activeProduct)
    rootComp = design.rootComponent
    
    L, W, H_t, Elev = [inputs.itemById(n).value for n in ['ext_length', 'ext_width', 'target_height', 'leg_elevation']]
    PW, PT, LW, LN = [inputs.itemById(n).value for n in ['picket_width', 'picket_thick', 'leg_wide', 'leg_narrow']]
    O, RW, CW, CI = [inputs.itemById(n).value for n in ['rim_overhang', 'rim_width', 'cleat_width', 'cleat_inset']]

    count = max(1, math.floor(H_t / PW))
    leg_h_expr = f"({count} * {inputs.itemById('picket_width').expression}) + {inputs.itemById('leg_elevation').expression}"

    # Clear previous preview components
    existing = rootComp.occurrences.itemByName("Picket Planter")
    if existing: existing.deleteMe()
    
    mainOcc = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    mainOcc.component.name = "Picket Planter"
    pc = mainOcc.component
    
    def sub(name):
        o = pc.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        o.component.name = name; return o.component

    comp_long, comp_short, comp_leg, comp_floor, comp_rim = [sub(n) for n in ["Long Walls", "Short Walls", "Legs", "Floor & Bracing", "Rim Cap"]]
    xy, z_axis = rootComp.xYConstructionPlane, rootComp.zConstructionAxis

    # Legs
    sk_w1 = draw_rect(comp_leg.sketches, xy, 0, 0, LW, PT); extrude_sketch(comp_leg, sk_w1, leg_h_expr)
    sk_n1 = draw_rect(comp_leg.sketches, xy, 0, PT, PT, LN); extrude_sketch(comp_leg, sk_n1, leg_h_expr)
    sk_w2 = draw_rect(comp_leg.sketches, xy, W-LW, 0, W, PT); extrude_sketch(comp_leg, sk_w2, leg_h_expr)
    sk_n2 = draw_rect(comp_leg.sketches, xy, W-PT, PT, W, LN); extrude_sketch(comp_leg, sk_n2, leg_h_expr)
    sk_w3 = draw_rect(comp_leg.sketches, xy, 0, L-PT, LW, L); extrude_sketch(comp_leg, sk_w3, leg_h_expr)
    sk_n3 = draw_rect(comp_leg.sketches, xy, 0, L-LN, PT, L-PT); extrude_sketch(comp_leg, sk_n3, leg_h_expr)
    sk_w4 = draw_rect(comp_leg.sketches, xy, W-LW, L-PT, W, L); extrude_sketch(comp_leg, sk_w4, leg_h_expr)
    sk_n4 = draw_rect(comp_leg.sketches, xy, W-PT, L-LN, W, L-PT); extrude_sketch(comp_leg, sk_n4, leg_h_expr)

    wp_in = pc.constructionPlanes.createInput(); wp_in.setByOffset(xy, adsk.core.ValueInput.createByReal(Elev))
    wp = pc.constructionPlanes.add(wp_in)
    
    # Sides
    for x_pos in [PT, W-2*PT]:
        sk = draw_rect(comp_long.sketches, wp, x_pos, PT, x_pos+PT, L-PT)
        ext = extrude_sketch(comp_long, sk, 'picket_width')
        if count > 1:
            pat_in = comp_long.features.rectangularPatternFeatures.createInput(adsk.core.ObjectCollection.createWithArray(list(ext.bodies)), z_axis, adsk.core.ValueInput.createByReal(count), adsk.core.ValueInput.createByReal(PW), adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
            comp_long.features.rectangularPatternFeatures.add(pat_in)
    
    # Front/Back
    for y_pos in [PT, L-2*PT]:
        sk = draw_rect(comp_short.sketches, wp, 2*PT, y_pos, W-2*PT, y_pos+PT)
        ext = extrude_sketch(comp_short, sk, 'picket_width')
        if count > 1:
            pat_in = comp_short.features.rectangularPatternFeatures.createInput(adsk.core.ObjectCollection.createWithArray(list(ext.bodies)), z_axis, adsk.core.ValueInput.createByReal(count), adsk.core.ValueInput.createByReal(PW), adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
            comp_short.features.rectangularPatternFeatures.add(pat_in)

    # Cleats
    sk_cl = draw_rect(comp_floor.sketches, wp, 2*PT, 2*PT+CI, 2*PT+CW, L-2*PT-CI); extrude_sketch(comp_floor, sk_cl, 'picket_thick')
    sk_cr = draw_rect(comp_floor.sketches, wp, W-2*PT-CW, 2*PT+CI, W-2*PT, L-2*PT-CI); extrude_sketch(comp_floor, sk_cr, 'picket_thick')
    
    # Floor - Spans from interior of Front wall (2*PT) to interior of Back wall (L-2*PT)
    fp_in = pc.constructionPlanes.createInput(); fp_in.setByOffset(wp, adsk.core.ValueInput.createByString('picket_thick'))
    fp = pc.constructionPlanes.add(fp_in)
    
    # Total interior length for slats
    avail_l = L - 4*PT
    num_full = math.floor(avail_l / PW)
    remainder = avail_l - (num_full * PW)
    
    # Place full width slats butted against each other
    for j in range(num_full):
        y_s = 2*PT + j*PW
        sk = draw_rect(comp_floor.sketches, fp, 2*PT, y_s, W-2*PT, y_s + PW)
        extrude_sketch(comp_floor, sk, 'picket_thick')
        
    # Place rip cut slat to fill the remaining interior gap
    if remainder > 0.01:
        y_s = 2*PT + num_full*PW
        sk = draw_rect(comp_floor.sketches, fp, 2*PT, y_s, W-2*PT, y_s + remainder)
        objs = adsk.core.ObjectCollection.create()
        for prof in sk.profiles: objs.add(prof)
        ext_input = comp_floor.features.extrudeFeatures.createInput(objs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByString('picket_thick'))
        comp_floor.features.extrudeFeatures.add(ext_input)

    # Rim
    rp_in = pc.constructionPlanes.createInput(); rp_in.setByOffset(xy, adsk.core.ValueInput.createByString(leg_h_expr))
    rp = pc.constructionPlanes.add(rp_in)
    f_p = [(-O,-O), (W+O,-O), (W+O-RW,-O+RW), (-O+RW,-O+RW)]
    b_p = [(-O,L+O), (W+O,L+O), (W+O-RW,L+O-RW), (-O+RW,L+O-RW)]
    l_p = [(-O,-O), (-O+RW,-O+RW), (-O+RW,L+O-RW), (-O,L+O)]
    r_p = [(W+O,-O), (W+O-RW,-O+RW), (W+O-RW,L+O-RW), (W+O,L+O)]
    for pts in [f_p, b_p, l_p, r_p]:
        sk = draw_polygon(comp_rim.sketches, rp, pts); extrude_sketch(comp_rim, sk, 'picket_thick')
    return pc

def export_bom(pc, inputs):
    folder_dialog = ui.createFolderDialog()
    folder_dialog.title = "Select Folder for BOM"
    if folder_dialog.showDialog() == adsk.core.DialogResults.DialogOK:
        bodies = []
        for occ in pc.allOccurrences:
            for b in occ.component.bRepBodies:
                if not b.isSolid: continue
                bb = b.boundingBox
                d = sorted([(bb.maxPoint.x-bb.minPoint.x)/2.54, (bb.maxPoint.y-bb.minPoint.y)/2.54, (bb.maxPoint.z-bb.minPoint.z)/2.54])
                bodies.append({'name': occ.component.name, 'thick': d[0], 'width': d[1], 'length': d[2]})
        
        stock_l = inputs.itemById('stock_length').value / 2.54
        kerf = inputs.itemById('kerf').value / 2.54
        cost = inputs.itemById('cost').value
        # Reusing the First-Fit Decreasing optimization logic
        groups = {}
        for b in bodies:
            t, w = round(b['thick'], 3), round(b['width'], 3)
            if t > w: t, w = w, t
            key = (t, w)
            if key not in groups: groups[key] = []
            groups[key].append(b)
        layout = {}; total_boards = 0
        for key, parts in groups.items():
            parts = sorted(parts, key=lambda x: x['length'], reverse=True)
            bins = []
            for part in parts:
                placed = False
                for i in range(len(bins)):
                    used = sum(p['length'] for p in bins[i]) + len(bins[i]) * kerf
                    if used + part['length'] <= stock_l:
                        bins[i].append(part); placed = True; break
                if not placed: bins.append([part])
            layout[key] = bins; total_boards += len(bins)
        
        path = os.path.join(folder_dialog.folder, 'planter_bom_and_cutlist.csv')
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['--- PROJECT SUMMARY ---'])
            w.writerow(['Total Boards:', total_boards, 'Cost:', f'${total_boards*cost:.2f}'])
            w.writerow([]); w.writerow(['--- BOM ---'])
            w.writerow(['Part', 'Qty', 'T', 'W', 'L'])
            counts = {}
            for b in bodies:
                k = (b['name'], round(b['thick'],3), round(b['width'],3), round(b['length'],3))
                counts[k] = counts.get(k, 0) + 1
            for k, q in counts.items(): w.writerow([k[0], q, k[1], k[2], f'{k[3]:.2f}'])
            w.writerow([]); w.writerow(['--- CUT LIST ---'])
            for key, bins in layout.items():
                w.writerow([f'Stock: {key[0]}" x {key[1]}"'])
                for i, bl in enumerate(bins): w.writerow([f' Board #{i+1}', ", ".join([f"{p['name']} ({p['length']:.2f}\")" for p in bl])])
        ui.messageBox(f"BOM exported to:\n{path}")

# --- UI Handlers ---
class PlanterCommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            build_model(inputs) # Final build
            save_settings(inputs)
        except: ui.messageBox(traceback.format_exc())

class PlanterCommandExecutePreviewHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        global _needs_update
        if _needs_update:
            try:
                build_model(args.firingEvent.sender.commandInputs)
                args.isValidResult = True
                _needs_update = False
            except: pass

class PlanterCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        global _needs_update
        try:
            cmd_input = args.input
            if cmd_input.id == 'btn_update':
                _needs_update = True
            elif cmd_input.id == 'btn_bom':
                inputs = args.firingEvent.sender.commandInputs
                pc = build_model(inputs)
                export_bom(pc, inputs)
        except: pass

class PlanterCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        cmd = args.command
        cmd.isExecutedWhenOk = True # OK finishes the model
        
        onEx = PlanterCommandExecuteHandler(); cmd.execute.add(onEx); handlers.append(onEx)
        onPr = PlanterCommandExecutePreviewHandler(); cmd.executePreview.add(onPr); handlers.append(onPr)
        onCh = PlanterCommandInputChangedHandler(); cmd.inputChanged.add(onCh); handlers.append(onCh)
        
        inputs = cmd.commandInputs
        s = load_settings()
        
        inputs.addValueInput('ext_length', 'Ext Length', 'in', adsk.core.ValueInput.createByString(s['ext_length']))
        inputs.addValueInput('ext_width', 'Ext Width', 'in', adsk.core.ValueInput.createByString(s['ext_width']))
        inputs.addValueInput('target_height', 'Target Height', 'in', adsk.core.ValueInput.createByString(s['target_height']))
        inputs.addValueInput('leg_elevation', 'Leg Elevation', 'in', adsk.core.ValueInput.createByString(s['leg_elevation']))
        inputs.addValueInput('picket_width', 'Picket Width', 'in', adsk.core.ValueInput.createByString(s['picket_width']))
        inputs.addValueInput('picket_thick', 'Picket Thick', 'in', adsk.core.ValueInput.createByString(s['picket_thick']))
        inputs.addValueInput('leg_wide', 'Leg Wide', 'in', adsk.core.ValueInput.createByString(s['leg_wide']))
        inputs.addValueInput('leg_narrow', 'Leg Narrow', 'in', adsk.core.ValueInput.createByString(s['leg_narrow']))
        inputs.addValueInput('rim_overhang', 'Rim Overhang', 'in', adsk.core.ValueInput.createByString(s['rim_overhang']))
        inputs.addValueInput('rim_width', 'Rim Width', 'in', adsk.core.ValueInput.createByString(s['rim_width']))
        inputs.addValueInput('cleat_width', 'Cleat Width', 'in', adsk.core.ValueInput.createByString(s['cleat_width']))
        inputs.addValueInput('cleat_inset', 'Cleat Offset', 'in', adsk.core.ValueInput.createByString(s['cleat_inset']))
        inputs.addValueInput('stock_length', 'Stock Length', 'in', adsk.core.ValueInput.createByString(s['stock_length']))
        inputs.addValueInput('kerf', 'Saw Kerf', 'in', adsk.core.ValueInput.createByString(s['kerf']))
        inputs.addValueInput('cost', 'Cost/Board', '', adsk.core.ValueInput.createByReal(float(s['cost'])))
        
        inputs.addBoolValueInput('btn_update', 'Update Drawing', False, '', True)
        inputs.addBoolValueInput('btn_bom', 'Build BOM & Cut List', False, '', True)

def run(context):
    try:
        global app, ui; app = adsk.core.Application.get(); ui = app.userInterface
        cmdDef = ui.commandDefinitions.itemById('PicketPlanterFinalV2')
        if not cmdDef: cmdDef = ui.commandDefinitions.addButtonDefinition('PicketPlanterFinalV2', 'Picket Planter (Fixed Update)', '')
        onCr = PlanterCommandCreatedHandler(); cmdDef.commandCreated.add(onCr); handlers.append(onCr)
        cmdDef.execute()
        adsk.autoTerminate(False)
    except: ui.messageBox(traceback.format_exc())

def stop(context):
    try:
        cmdDef = ui.commandDefinitions.itemById('PicketPlanterFinalV2')
        if cmdDef: cmdDef.deleteMe()
    except: pass
