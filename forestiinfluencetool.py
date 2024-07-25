import arcpy, os
from arcpy import env
from arcpy.sa import *
import commonstuff as cs


# To allow overwriting the outputs change the overwrite option to true.
arcpy.env.overwriteOutput = True

# Setting the workspace environment.
# setting the workspace basically meant for outputs (has to be a gdb) 
# arcpy.env.workspace = r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/Mosaic_Layers.gdb"

# proposed_blocks = r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/Mosaic_Layers.gdb/Subsetting_RB_Test"
# cwh_layer = r"C:/projects/mosaic/MosaicForestInfluenceTool_Data/Data/TP14i.gdb/TP14i_2022_Mosaic_LU"

area_dic = {'total_area': 0, 'subset_area': 0}
subset_of_propoductive_area = {}
objectid = 0

# Path to the new feature class
new_fc = "NewFeatureClass"

# create temporary gbd if one doesn't exist at the location specified
def create_temp_gdb(temp_gdb_location):
    if not arcpy.Exists(temp_gdb_location):
        arcpy.CreateFileGDB_management(temp_gdb_location, "/temp.gdb")
        cs.writelog("Created a new file geodatabase at: " + temp_gdb_location)
    else:
        cs.writelog("File geodatabase already exists at: " + temp_gdb_location)

def create_table():
    # create a table to store the results if it doesn't exist
    if not arcpy.Exists("Results"):
        arcpy.CreateTable_management(arcpy.env.workspace, "Results")
        arcpy.AddField_management("Results", "Block_ID", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management("Results", "Immediate_OM", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        cs.writelog("Created a new table to store the results")
    else:
        cs.writelog("Table already exists")

def buffer(proposed_blocks, objectid):
    # Process: Buffer only the selected features and dissolve the output
    # in the event of returning back all the fields in the feature class, this would imply a selection of the entire feature class

    # iterate through the selected features and note the subsetting names
    names = ""
    for row in arcpy.da.SearchCursor(proposed_blocks, ['SubSettingName']):
        cs.writelog(row[0])
        names += row[0] + ";"
    
    # write the names list to the table
    with arcpy.da.InsertCursor("Results", ['Block_ID']) as cursor:
        objectid = cursor.insertRow([names])


    # buffer the selected features   
    arcpy.Buffer_analysis(proposed_blocks, "Buffer", "2000 Meters", "FULL", "ROUND", "ALL", "", "PLANAR")

    # union the buffered features with the selection and copy over the original buffer to a new feature class
    arcpy.Union_analysis([proposed_blocks, "Buffer"], "Union", "ALL", "", "GAPS")




    # Define the condition to select the specific row
    condition_field = "SubSettingName"
    condition_value = ""  # Change as per your requirement

    # Get the spatial reference of the existing feature class
    spatial_ref = arcpy.Describe("Union").spatialReference

    # Create the new feature class with the same schema
    arcpy.CreateFeatureclass_management(arcpy.env.workspace, new_fc, "POLYGON", "Union", "SAME_AS_TEMPLATE", "SAME_AS_TEMPLATE", spatial_ref)

    # Define the fields to be copied
    fields = [field.name for field in arcpy.ListFields("Union") if field.type not in ("OID", "Geometry")]

    # Add geometry field
    fields.append("SHAPE@")

    # Use a search cursor to select the specific row from the existing feature class
    with arcpy.da.SearchCursor("Union", fields) as search_cursor:
        for row in search_cursor:
            if row[fields.index(condition_field)] == condition_value:
                selected_row = row
                break

    # Use an insert cursor to insert the selected row into the new feature class
    with arcpy.da.InsertCursor(new_fc, fields) as insert_cursor:
        insert_cursor.insertRow(selected_row)


    return objectid

def intersect():
    # get the intersection bewteen the buffer and the cwh layer
    arcpy.Intersect_analysis([cwh_layer, new_fc], "Intersect", "ALL", "", "INPUT")

    # remove the cwh layer from the intersected features with manifold  

def area(objectid):
    # write the results to a new field in the original selected feature

    # arcpy.AddField_management(proposed_blocks, "Immediate_om", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    
    # get total area of the intersected features per block
    with arcpy.da.SearchCursor("Intersect", ['SHAPE@AREA', 'PROJ_AGE', 'BGC_ZONE']) as cursor:
        for row in cursor:
            # sum all the area per block and store it in a dictionary
            area_dic['total_area'] += row[0]
            # print(row[2])

            # get the area from the cwh layer where PROJ_AGE is greater than 80 when BGC_ZONE = cwh and PROJ_AGE > 120 when BGC_ZONE = mh
            if row[2] != None and row[1] > 80 and row[2] == "CWH":
                area_dic['subset_area'] += row[0]
            elif row[2] != None and row[1] > 120 and row[2] == "MH":
                area_dic['subset_area'] += row[0]


    immediate_om_value = area_dic['subset_area'] / area_dic['total_area'] * 100
    cs.writelog("Immediate OM value is: " + str(immediate_om_value) + "%")


    # Create an insert cursor
    with arcpy.da.UpdateCursor("Results", ['OBJECTID', 'Immediate_om']) as cursor:
        for row in cursor:
            if row[0] == objectid:
                row[1] = immediate_om_value
                cursor.updateRow(row)



if __name__ == "__main__":
    proposed_blocks = arcpy.GetParameterAsText(0) 
    cwh_layer = arcpy.GetParameterAsText(1)  
    temp_gdb_location = arcpy.GetParameterAsText(2) 

    create_temp_gdb(temp_gdb_location)
    arcpy.env.workspace = os.path.join(temp_gdb_location, "temp.gdb")
    create_table()

    objectid = buffer(proposed_blocks, objectid)
    cs.writelog("Buffered the proposed blocks")
    cs.writelog("Object ID is: " + str(objectid))
    intersect()
    cs.writelog("Intersected the buffered proposed blocks with the cwh layer")
    area(objectid)
    cs.writelog("Calculated the area of the intersected features")

    

