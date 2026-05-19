# Picket Planter for Autodesk Fusion 360

A production-ready parametric script for Autodesk Fusion 360 that designs, optimizes, and generates a Bill of Materials (BOM) for "Three Picket" style planter boxes.

![Planter Box Preview](https://via.placeholder.com/800x450.png?text=Parametric+Planter+Box+Preview)

## Features

- **Parametric Design**: Adjust length, width, height, leg elevation, and more. Dimensions represent absolute outer boundaries.
- **Dynamic Manual Preview**: Tweak parameters and update the 3D model manually via the "Update Drawing" button to maintain performance.
- **Smart Floor Construction**: Automatically calculates standard picket slats (5.5" default) and generates a single rip-cut filler board for a gap-free solid floor.
- **1D Bin-Packing Optimization**: Employs a First-Fit Decreasing (FFD) algorithm to map parts onto commercial stock lengths (e.g., 96"), factoring in saw blade kerf.
- **BOM & Cut List Export**: Generates a detailed CSV including a project cost summary, component table, and board-by-board cut layout.
- **Persistent Settings**: Remembers your last-used parameters across sessions via a local JSON configuration.
- **Professional Assembly Logic**:
    - Legs on the exterior.
    - End walls recessed between side walls (butt joints).
    - Cleats flush-mounted to side walls with configurable offsets from end walls.

## Installation

1. **Download the Script**:
   - Clone this repository or download the `PicketPlanters.py` and `PicketPlanters.manifest` files.
2. **Locate Fusion 360 Scripts Folder**:
   - Open Autodesk Fusion 360.
   - Go to **Utilities > Add-ins > Scripts and Add-ins** (or press `Shift + S`).
   - Click the **Scripts** tab, then click the **folder icon** ("Reveal Support File in Explorer/Finder") next to any script.
3. **Install the Script**:
   - Create a folder named `PicketPlanters` inside the Fusion 360 `Scripts` folder.
   - Place `PicketPlanters.py`, `PicketPlanters.manifest`, and any other icons/files from this repo into that folder.
4. **Run the Script**:
   - Back in the Fusion 360 **Scripts and Add-ins** dialog, click the **My Scripts** folder.
   - Select **Picket Planter (Fixed Update)** and click **Run**.

## Usage

1. **Adjust Parameters**: Fill in your target external dimensions and stock details.
2. **Update Drawing**: Click the **Update Drawing** button to see the 3D model change.
3. **Build BOM**: Click **Build BOM & Cut List**, select a destination folder, and the script will generate your shopping list and cut map.
4. **Finalize**: Click **OK** to commit the planter to your workspace.

## Parameters

| Parameter | Description |
| :--- | :--- |
| **Ext Length/Width** | Absolute outer footprint of the planter. |
| **Target Height** | The height you want the walls to reach. Script calculates board count automatically. |
| **Leg Elevation** | The air gap between the ground and the bottom of the box. |
| **Picket Width/Thick** | Raw dimensions of your cedar/pine pickets (e.g., 5.5" x 0.625"). |
| **Cleat Width/Offset** | Internal floor support dimensions and gap from end walls. |
| **Stock Length/Kerf** | Commercial board length (e.g., 96") and your saw blade thickness. |

## License

This project is licensed under the MIT License - see the LICENSE file for details.
