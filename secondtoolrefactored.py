import arcpy
import arcpy.management
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import commonstuff as cs

# from fpdf import FPDF

# Function to set up workspace and geodatabase
def setup_workspace(workspace, gdb_name):
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutput = True
    gdb_path = os.path.join(workspace, gdb_name)
    if not arcpy.Exists(gdb_path):
        arcpy.CreateFileGDB_management(workspace, gdb_name)
    return gdb_path

# Function to load input data
def load_input_data(cutblock_path, retention_areas_path, non_merch_areas_path, tree_layer_path, chm_path, adjacent_cutblocks_path):
    return {
        "cutblock": cutblock_path,
        "retention_areas": retention_areas_path,
        "non_merch_areas": non_merch_areas_path,
        "tree_layer": tree_layer_path,
        "chm": chm_path,
        "adjacent_cutblocks": adjacent_cutblocks_path
    }

# Function to determine net harvestable area
def determine_net_harvestable_area(cutblock, non_merch_areas, retention_areas, gdb_path):
    net_harvestable_area = os.path.join(gdb_path, "net_harvestable_area")
    temp_net_harvestable_area = os.path.join(gdb_path, "temp_net_harvestable_area")
    arcpy.Erase_analysis(cutblock, non_merch_areas, temp_net_harvestable_area)
    arcpy.Erase_analysis(temp_net_harvestable_area, retention_areas, net_harvestable_area)
    return net_harvestable_area

# Function to clip optional tree layer to the cutblock boundary
def clip_tree_layer(tree_layer, cutblock, gdb_path):
    if arcpy.Exists(tree_layer):
        clipped_tree_layer = os.path.join(gdb_path, "clipped_tree_layer")
        arcpy.Clip_analysis(tree_layer, cutblock, clipped_tree_layer)
        return clipped_tree_layer
    return None

# Function to process CHM
def process_chm_or_trees(chm, cutblock, adjacent_cutblocks,net_harvestable_area, gdb_path, tree_layer=None):
    
    if arcpy.Exists(tree_layer):
        cs.writelog("Tree layer exists")

        tree_layer_raster = os.path.join(gdb_path, "tree_layer_raster")
        arcpy.PointToRaster_conversion(tree_layer, "RASTERVALU", tree_layer_raster, cellsize=5)

        extended_cutblock = os.path.join(gdb_path, "extended_cutblock")
        arcpy.Buffer_analysis(cutblock, extended_cutblock, "100 Meters", "OUTSIDE_ONLY", "ROUND", "ALL", None, "PLANAR")
        
        clipped_chm = os.path.join(gdb_path, "clipped_chm")
        arcpy.Clip_management(tree_layer_raster, "", clipped_chm, extended_cutblock, "", "ClippingGeometry", "MAINTAIN_EXTENT")
        
        # clipped_trees = os.path.join(gdb_path, "clipped_trees")
        # arcpy.Clip_management(tree_layer_raster, "", clipped_trees, cutblock, "", "ClippingGeometry", "MAINTAIN_EXTENT")


        # arcpy.Append_management(clipped_trees, clipped_chm, "NO_TEST")


        if arcpy.Exists(adjacent_cutblocks):
            temp_final_clipped_chm = os.path.join(gdb_path, "temp_final_clipped_chm")
            arcpy.Erase_analysis(clipped_chm, adjacent_cutblocks, temp_final_clipped_chm)
            clipped_chm = temp_final_clipped_chm
            generalized_chm = os.path.join(gdb_path, "generalized_chm")
            arcpy.Resample_management(clipped_chm, generalized_chm, "5", "BILINEAR")
            return generalized_chm
        
        generalized_chm = os.path.join(gdb_path, "generalized_chm")
        arcpy.Resample_management(clipped_chm, generalized_chm, "5", "BILINEAR")

        return generalized_chm
    
    elif arcpy.Exists(chm):
        buffer4m = os.path.join(gdb_path, "buffer4m")
        extended_cutblock = os.path.join(gdb_path, "extended_cutblock")
        arcpy.Buffer_analysis(cutblock, buffer4m, "4 Meters")
        arcpy.Buffer_analysis(buffer4m, extended_cutblock, "96 Meters", "OUTSIDE_ONLY", "ROUND", "ALL", None, "PLANAR")

        if arcpy.Exists(adjacent_cutblocks):
            # reverse the current selection of cutblock
            arcpy.SelectLayerByAttribute_management(cutblock, "SWITCH_SELECTION")
            # clip the extended cutblock with the adjacent cutblocks
            temp_extended_cutblock = os.path.join(gdb_path, "temp_extended_cutblock")
            arcpy.Erase_analysis(extended_cutblock, cutblock, temp_extended_cutblock)
            extended_cutblock = temp_extended_cutblock
            # reverse the selection back
            arcpy.SelectLayerByAttribute_management(cutblock, "SWITCH_SELECTION")

        
        clipped_chm = os.path.join(gdb_path, "clipped_chm")
        arcpy.Clip_management(chm, "", clipped_chm, extended_cutblock, "", "ClippingGeometry", "MAINTAIN_EXTENT")
        
        # if arcpy.Exists(adjacent_cutblocks):
        #     temp_final_clipped_chm = os.path.join(gdb_path, "temp_final_clipped_chm")
        #     arcpy.Clip_management(clipped_chm, "", temp_final_clipped_chm, adjacent_cutblocks, "", "ClippingGeometry", "MAINTAIN_EXTENT")            
        #     clipped_chm = temp_final_clipped_chm
        
        generalized_chm = os.path.join(gdb_path, "generalized_chm")
        arcpy.Resample_management(clipped_chm, generalized_chm, "5", "BILINEAR")
        
        return generalized_chm
    return None

# Function to convert CHM to points and process heights
def convert_chm_to_points(generalized_chm, gdb_path):
    chm_points = os.path.join(gdb_path, "chm_points")
    arcpy.RasterToPoint_conversion(generalized_chm, chm_points, "VALUE")
    
    arcpy.AddField_management(chm_points, 'Height', 'DOUBLE')
    with arcpy.da.UpdateCursor(chm_points, ['grid_code', 'Height']) as cursor:
        for row in cursor:
            row[1] = max(row[0], 0)  # Round negative values to 0
            cursor.updateRow(row)
    
    return chm_points

# Function to buffer points and merge into tree height buffers
def buffer_and_merge_points(chm_points, gdb_path):
    tree_height_buffers = os.path.join(gdb_path, "tree_height_buffers")
    arcpy.Buffer_analysis(chm_points, tree_height_buffers, "Height", "FULL", "ROUND", "ALL", None, "PLANAR")
    
    return tree_height_buffers

# Function to clip tree height buffers to net harvestable area
def clip_tree_height_buffers(tree_height_buffers, net_harvestable_area, gdb_path):
    clipped_tree_height_buffers = os.path.join(gdb_path, "clipped_tree_height_buffers")
    arcpy.Clip_analysis(tree_height_buffers, net_harvestable_area, clipped_tree_height_buffers)
    return clipped_tree_height_buffers

# Function to buffer and add single trees
def buffer_and_add_single_trees(cutblock, single_trees, clipped_tree_height_buffers, gdb_path):
    if arcpy.Exists(single_trees):
        # clip single trees to the cutblock
        clipped_single_trees = os.path.join(gdb_path, "clipped_single_trees")
        arcpy.Clip_analysis(single_trees, cutblock, clipped_single_trees)
        buffered_single_trees = os.path.join(gdb_path, "buffered_single_trees")
        unioned_trees = os.path.join(gdb_path, "unioned_trees")
        arcpy.Buffer_analysis(clipped_single_trees, buffered_single_trees, "RASTERVALU", "OUTSIDE_ONLY", "ROUND", "ALL", None, "PLANAR")
        arcpy.Union_analysis([buffered_single_trees, clipped_tree_height_buffers], unioned_trees)
        # arcpy.Append_management(buffered_single_trees, clipped_tree_height_buffers, "NO_TEST")

# Function to calculate areas
def calculate_areas(net_harvestable_area, clipped_tree_height_buffers, retention_areas, non_merch_areas):
    net_harvestable_area_size = sum([r[0] for r in arcpy.da.SearchCursor(net_harvestable_area, ["SHAPE@AREA"])])
    forest_influence_area_size = sum([r[0] for r in arcpy.da.SearchCursor(clipped_tree_height_buffers, ["SHAPE@AREA"])])
    retention_area_size = sum([r[0] for r in arcpy.da.SearchCursor(retention_areas, ["SHAPE@AREA"])])
    non_merch_area_size = sum([r[0] for r in arcpy.da.SearchCursor(non_merch_areas, ["SHAPE@AREA"])])
    return net_harvestable_area_size, forest_influence_area_size, retention_area_size, non_merch_area_size

def create_output_image(clipped_tree_height_buffers, output_image_path):
    # Step 17: Load and display the forest influence layer in the open MXD document
    mxd_path = "CURRENT"  # Update with the path to your MXD
    mxd = arcpy.mapping.MapDocument(mxd_path)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    forest_influence_layer = arcpy.mapping.Layer(clipped_tree_height_buffers)
    arcpy.mapping.AddLayer(df, forest_influence_layer, "TOP")
    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()
    mxd.save()

    # Export an image of the map and forest influence layer to a temporary location
    arcpy.mapping.ExportToPNG(mxd, output_image_path)
    return output_image_path

# Function to generate report dictionary
def generate_report_dict(block_id, net_harvestable_area_size, forest_influence_area_size, retention_area_size, non_merch_area_size, single_trees, output_image):
    report = {
        "Block ID": block_id,
        "Block gross area": net_harvestable_area_size + retention_area_size + non_merch_area_size,
        "Retention area": retention_area_size,
        "Non merch/non forest area": non_merch_area_size,
        "Harvestable area": net_harvestable_area_size,
        "Number of single trees": arcpy.GetCount_management(single_trees).getOutput(0) if arcpy.Exists(single_trees) else 0,
        "Area of Forest Influence": forest_influence_area_size,
        "Percent harvestable area covered by Forest Influence": (forest_influence_area_size / net_harvestable_area_size) * 100,
        "Forest Influence Threshold Message": "Forest influence is greater than 50%" if (forest_influence_area_size / net_harvestable_area_size) * 100 > 50 else "Forest influence is less than 50%",
        "Map Image": output_image
    }
    return report

# Function to generate PDF report using ReportLab
def generate_pdf_report_reportlab(report, output_path):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Forest Influence Report")

    c.setFont("Helvetica", 12)
    y_position = height - 80
    for key, value in report.items():
        if key == "Map Image":
            c.drawString(100, y_position, "{key}:".format(key=key))
            y_position -= 20
            c.drawImage(value, 100, y_position - 200, width=400, height=200)
            y_position -= 220
        else:
            c.drawString(100, y_position, "{key}: {value}".format(key=key, value=value))
            y_position -= 20

    c.save()

# Main function to run all steps
def main():
    # Define paths
    # cutblock_path =  r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/Mosaic_Layers.gdb/Subsetting_RB_Test"
    # retention_areas_path = r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/Mosaic_Layers.gdb/Retention"
    # non_merch_areas_path = r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/Mosaic_Layers.gdb/Silv_NP"
    # tree_layer_path = r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/Mosaic_Layers.gdb/Trees"  # Optional
    # chm_path = r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/Mosaic_Layers.gdb/StandHeight1m"
    # adjacent_cutblocks_path = "path/to/adjacent_cutblocks.shp"
    # workspace = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data"
    # gdb_name = "temp.gdb"

    # single_trees_path = "path/to/single_trees.shp"  # Optional
    # block_id = "your_block_id"
    # output_image = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/forest_influence_map.png"
    # output_pdf_path = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/report.pdf"

    cutblock =  arcpy.GetParameterAsText(0)
    retention_areas = arcpy.GetParameterAsText(1) 
    non_merch_areas = arcpy.GetParameterAsText(2)
    tree_layer= arcpy.GetParameterAsText(3)
    chm = arcpy.GetParameterAsText(4)
    adjacent_cutblocks = arcpy.GetParameterAsText(5)
    workspace = arcpy.GetParameterAsText(6)
    gdb_name = "temp1.gdb"

    single_trees_path = arcpy.GetParameterAsText(7)  # Optional
    block_id = "your_block_id"
    output_image_path = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/forest_influence_map.png"
    output_pdf_path = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/report.pdf"


    # Setup workspace and geodatabase
    gdb_path = setup_workspace(workspace, gdb_name)
    cs.writelog("Workspace and geodatabase set up at:", gdb_path)

    # Get block id with search cursor
    with arcpy.da.SearchCursor(cutblock, ["SubSettingName"]) as cursor:
        for row in cursor:
            block_id = row[0]
            break

        
    # Determine net harvestable area
    net_harvestable_area = determine_net_harvestable_area(cutblock, non_merch_areas, retention_areas, gdb_path)
    cs.writelog("Net harvestable area determined")

    # Clip tree layer
    clipped_tree_layer = clip_tree_layer(tree_layer, cutblock, gdb_path)
    cs.writelog("Tree layer clipped")

    # Process CHM
    generalized_chm = process_chm_or_trees(chm, cutblock, adjacent_cutblocks, net_harvestable_area, gdb_path, tree_layer)
    cs.writelog("CHM processed")

    # Convert CHM to points and process heights
    chm_points = convert_chm_to_points(generalized_chm, gdb_path)
    cs.writelog("CHM converted to points and heights processed")

    # Buffer and merge points
    tree_height_buffers = buffer_and_merge_points(chm_points, gdb_path)
    cs.writelog("Points buffered and merged")

    # Clip tree height buffers
    clipped_tree_height_buffers = clip_tree_height_buffers(tree_height_buffers, net_harvestable_area, gdb_path)
    cs.writelog("Tree height buffers clipped")

    # Buffer and add single trees
    buffer_and_add_single_trees(cutblock, single_trees_path, clipped_tree_height_buffers, gdb_path)
    cs.writelog("Single trees buffered and added")

    # Calculate areas
    net_harvestable_area_size, forest_influence_area_size, retention_area_size, non_merch_area_size = calculate_areas(net_harvestable_area, clipped_tree_height_buffers, retention_areas, non_merch_areas)
    cs.writelog("Areas calculated")

    # Create the output image
    output_image = create_output_image(clipped_tree_height_buffers, output_image_path)
    cs.writelog("Output image created")

    # Generate report dictionary
    report = generate_report_dict(block_id, net_harvestable_area_size, forest_influence_area_size, retention_area_size, non_merch_area_size, single_trees_path, output_image)


    # Generate PDF report
    generate_pdf_report_reportlab(report, output_pdf_path)
    print("PDF report generated at:", output_pdf_path)

if __name__ == "__main__":
    main()
