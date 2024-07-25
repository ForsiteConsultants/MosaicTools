import arcpy
import os
import csv

# Set workspace
arcpy.env.workspace = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data"
arcpy.env.overwriteOutput = True

# Create a temporary geodatabase
gdb_path = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/temp.gdb"
if not arcpy.Exists(gdb_path):
    arcpy.CreateFileGDB_management("C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data", "temp.gdb")

# Load input data
cutblock = r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/Mosaic_Layers.gdb/Subsetting_RB_Test"
retention_areas = r"C:\projects\mosaic\MosaicForestInfluenceTool_Data\Data\Mosaic_Layers.gdb\Retention"
non_merch_areas = r"C:\projects\mosaic\MosaicForestInfluenceTool_Data\Data\Mosaic_Layers.gdb\Silv_NP"
tree_layer = r"C:\projects\mosaic\MosaicForestInfluenceTool_Data\Data\Mosaic_Layers.gdb\Trees"  # Optional
chm = r"C:\projects\mosaic\MosaicForestInfluenceTool_Data\Data\Mosaic_Layers.gdb\StandHeight1m"
adjacent_cutblocks = r"path/to/adjacent_cutblocks.shp"


# Step 2: Determine net harvestable area by erasing non-merchantable areas from the cutblock
net_harvestable_area = os.path.join(gdb_path, "net_harvestable_area")
arcpy.Erase_analysis(cutblock, non_merch_areas, net_harvestable_area)

# Step 3: Clip the optional tree layer to the cutblock boundary
if arcpy.Exists(tree_layer):
    clipped_tree_layer = os.path.join(gdb_path, "clipped_tree_layer")
    arcpy.Clip_analysis(tree_layer, cutblock, clipped_tree_layer)

# Step 4: Confirm the existence of the CHM
if arcpy.Exists(chm):
    # Step 5: Clip CHM to an area approximately 100m beyond the cutblock boundary
    extended_cutblock = os.path.join(gdb_path, "extended_cutblock")
    arcpy.Buffer_analysis(cutblock, extended_cutblock, "100 Meters")
    
    clipped_chm = os.path.join(gdb_path, "clipped_chm")
    arcpy.Clip_management(chm, "", clipped_chm, extended_cutblock, "", "ClippingGeometry", "MAINTAIN_EXTENT")
    
    # Step 6: Buffer back from the edge of the net harvestable area by 4m
    buffered_area = os.path.join(gdb_path, "buffered_area")
    arcpy.Buffer_analysis(net_harvestable_area, buffered_area, "-4 Meters")
    
    # Step 7: Clip the CHM to the buffered block area
    final_clipped_chm = os.path.join(gdb_path, "final_clipped_chm")
    arcpy.Clip_management(clipped_chm, "", final_clipped_chm, buffered_area, "", "ClippingGeometry", "MAINTAIN_EXTENT")
    
    # Step 8: If using adjacent cutblocks, delete those areas from the clipped CHM
    if arcpy.Exists(adjacent_cutblocks):
        temp_final_clipped_chm = os.path.join(gdb_path, "temp_final_clipped_chm")
        arcpy.Erase_analysis(final_clipped_chm, adjacent_cutblocks, temp_final_clipped_chm)
        final_clipped_chm = temp_final_clipped_chm

    # Step 9: Convert the CHM to a more generalized 5m raster using Resample
    generalized_chm = os.path.join(gdb_path, "generalized_chm")
    arcpy.Resample_management(final_clipped_chm, generalized_chm, "5", "BILINEAR")

    # Step 10: Convert the 5m CHM to points
    # arcpy.AddField_management(generalized_chm, 'Height', 'DOUBLE')
    # with arcpy.da.UpdateCursor(generalized_chm, ['VALUE', 'Height']) as cursor:
    #     for row in cursor:
    #         row[1] = row[0]
    #         cursor.updateRow(row) 
    chm_points = os.path.join(gdb_path, "chm_points")
    arcpy.RasterToPoint_conversion(generalized_chm, chm_points, "VALUE")

    # Step 11.5: Add a new field called 'Height' to the CHM points
    arcpy.AddField_management(chm_points, 'Height', 'DOUBLE')
    with arcpy.da.UpdateCursor(chm_points, ['grid_code', 'Height']) as cursor:
        for row in cursor:
            row[1] = max(row[0], 0)  # Round negative values to 0
            cursor.updateRow(row)

    # Step 11: Buffer all of the extracted points by 1x the height attribute
    chm_point_buffers = os.path.join(gdb_path, "chm_point_buffers")
    arcpy.Buffer_analysis(chm_points, chm_point_buffers, 'Height')

    # Step 12: Merge the buffers into a single layer of tree height buffers
    tree_height_buffers = os.path.join(gdb_path, "tree_height_buffers")
    arcpy.Merge_management([chm_point_buffers], tree_height_buffers)

    # Step 13: Clip the tree height buffers to the inside of the net harvestable area
    clipped_tree_height_buffers = os.path.join(gdb_path, "clipped_tree_height_buffers")
    arcpy.Clip_analysis(tree_height_buffers, net_harvestable_area, clipped_tree_height_buffers)

    # Step 14: Buffer and add single trees, if being used (Assuming single trees layer exists)
    # single_trees = "path/to/single_trees.shp"  # Update the path if needed
    if arcpy.Exists(clipped_tree_layer):
        buffered_single_trees = os.path.join(gdb_path, "buffered_single_trees")
        arcpy.Buffer_analysis(clipped_tree_layer, buffered_single_trees, "1 Meter")
        arcpy.Append_management(buffered_single_trees, clipped_tree_height_buffers, "NO_TEST")

    # Step 15: Calculate the net harvestable areas and forest influence area
    net_harvestable_area_size = sum([r[0] for r in arcpy.da.SearchCursor(net_harvestable_area, ["SHAPE@AREA"])])
    forest_influence_area_size = sum([r[0] for r in arcpy.da.SearchCursor(clipped_tree_height_buffers, ["SHAPE@AREA"])])
    retention_area_size = sum([r[0] for r in arcpy.da.SearchCursor(retention_areas, ["SHAPE@AREA"])])
    non_merch_area_size = sum([r[0] for r in arcpy.da.SearchCursor(non_merch_areas, ["SHAPE@AREA"])])


    # Step 16: Load and display the forest influence layer in the open MXD document
    mxd_path = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/ForestInfluenceTest - Forsite.mxd"  # Update with the path to your MXD
    mxd = arcpy.mapping.MapDocument(mxd_path)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    forest_influence_layer = arcpy.mapping.Layer(clipped_tree_height_buffers)
    arcpy.mapping.AddLayer(df, forest_influence_layer, "TOP")
    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()
    mxd.save()

    # Step 17: Export an image of the map and forest influence layer to a temporary location
    output_image = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/forest_influence_map.png"
    arcpy.mapping.ExportToPNG(mxd, output_image)
    
    # Step 18: Generate an Esri report of attributes and calculations of forest influence
    # Generate the report
    report = {
        "Block ID": "your_block_id",  # Replace with your method of getting Block ID
        "Block gross area": net_harvestable_area_size + retention_area_size + non_merch_area_size,
        "Retention area": retention_area_size,
        "Non merch/non forest area": non_merch_area_size,
        "Harvestable area": net_harvestable_area_size,
        "Number of single trees": arcpy.GetCount_management(buffered_single_trees).getOutput(0) if arcpy.Exists(buffered_single_trees) else 0,
        "Area of Forest Influence": forest_influence_area_size,
        "Percent harvestable area covered by Forest Influence": (forest_influence_area_size / net_harvestable_area_size) * 100,
        "Forest Influence Threshold Message": "Forest influence is greater than 50%" if (forest_influence_area_size / net_harvestable_area_size) * 100 > 50 else "Forest influence is less than 50%",
        "Map Image": output_image
    }

    # Output report to CSV
    report_path = "C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/report.csv"
    with open(report_path, "w", newline='') as csvfile:
        fieldnames = list(report.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(report)

print("Processing complete.")
