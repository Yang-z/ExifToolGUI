# ExifToolGUI
ExifToolGUI is a graphical user interface for ExifTool.


## UI

- File list view: Each row represents a file, and each column represents a tag. Cells are directly editable.

- Metadata view: Every tab contains a set of tags of the selected file in file list. Tab of "All" displays all the tags of the selected file. Some preset tabs, such as "Datetime", contains the relevant tags. Tab of "Custom" is for customising. Tag values in metadata view are directly editable.

- Preview: Support preview for photo and video. Other types of file use file icon as preview.


## IO
### Read

- Tag names are exported in JSON format (-j), and full group names are required (-G:0:1:2:3:4:5:6:7). Tag names instead of descriptions
are always retruned by JSON, so no need to specified short output format (-s).

- Tag names are not necessarily displayed with full group names. Actually, GUI displays simplified tag groups according to settings.

- Separator string for tag values of list items is forced to be ";" (-sep ;).

- Tag values are exported as original values with no print conversion (-n) by default.

- Duplicate tags are allowed to be extracted (-a) by default.

- Tag values of unknown tags as well as unknown information from some binary data blocks are extracted (-U) by default.


### Write

- Click any cell to edit the value you want directly.

- GUI normally does not restrict values inputted. That means user can try to modify any tag by any value, but whether the edited value can be saved back to file depends on the ExifTool side. Excptions are made for GUI defined Virtual Tags and Formatting Tags. Inputted values for thoese tags could be modified (normalised) or rejected by GUI according to their definitions. See below:

    - For a GUI defined Formatting Tag, the inputted value would be normalised during editing. e.g. GUI would try to format the value of a defined datetime tag according to it's definition. If formatting fails, original user inputted value keeps.

    - For a GUI defined Virtual Tags, GUI would try to interpret the inputted value first, and if it's invaild, this editing will be abandoned.

- If auto-saving is not on (default), the edited values are cached but have not been written back to files. User should click the Save Button to write the edited values back to files. The edited but not saved cells is coloured to yellow. 

- Once the Save Button is click, the colour of edited cells would be changed to indicate whether saving is successful or not, i.e. green means successful while read means failed.

- If an edited value is failed to save, that means ExifTool does not support writting that tag or the value inputed does not meet the specified format of that tag. Refer to log to see the error information. Detailed doc could be found on the ExifTool official website.

- File modification date/time is preserved (-P) by default.

- Overwrite the original file when writing (-overwrite_original) by default.


## Virtual Tags
Current GUI defined Virtual Tags includes: Composite Tags, Conditional Tags, Casted Tags.

### Composite Tags
Tag name starts with "&". The value is a combination of normal tag's value or implicitly specified values.

- e.g.:  
    - "&EXIF:DateTimeOriginal": It's a combination of "EXIF:DateTimeOriginal", "EXIF:SubSecTimeOriginal" and "EXIF:OffsetTimeOriginal". It's value seems like "2023:07:08 20:09:10.87+08:00".

    - "&QuickTime:CreateDate": It's a combination of "QuickTime:CreateDate" and its implicitly specified timezone offset "+00:00". It's value seems like "2023:07:08 12:09:11+00:00".
    
- Composite tags are editable.
- Composite tags supports customisation.

### Conditional Tags
Tag name starts with "?". It falls back to another tag depends on conditions.

- e.g.:    
    - "?Timeline": If the file type is "jpge" or "tiff", it falls back to "&EXIF:DateTimeOriginal", while if the file type is "mp4", it falls back to "&QuickTime:CreateDate".
    
- Conditional tags are editable.
- Conditional tags supports customisation.

### Casted Tags
Tag name starts with "(type)", type could be any python types. The meaning of this kind tags is try to interpret the orginal value to the target type.

- e.g.:
    - "(datetime)File:FileName": Photos saved from some social apps always lost EXIF information but they are named with a timestamp, i.e. "XXXX1688818150873.jpg". "(datetime)File:FileName" will return the value of "2023:07:08 12:09:10.873+00:00". Although it's not the original datetime, it helps user to guess the original time roughly.

- Casted tags are not editable (read only).
- Casted tags supports customisation.


## Formatting Tags
Current GUI defined Formatting Tags includes: datatime tags.

### Datetime Tags
Defination of a detetime tag tells whether it is stored as UTC, whether the timezone offset is explicit specified and whether it support sub-second. Program formats value according to the information provided by the tag defination. 


## Functions

Some functions are defined to batch editing tags:
- rename: rename seleted file(s) by a combination of tag values.

- set value: set a values to tag(s) of seleted file(s).

- copy value: copy values of a specified tag to another specified tag (or other tags) of selected file(s).

- shift datetime: shift the datetime value by a timedelta, or to a specified time for selected file(s). One of "timedelta" or "to_datetime" should be specified. The current selected file is used as reference to calculated the timedelta if  "to_datetime" is not null but "timedelta" is null. Sorting table by target tag before choosing the reference file is recommended.

- reverse order: This function swap values of the specified tag head to tail sequentially between selected files.


## Settings
### ExifToolGUI options

- default:
    ```
    "auto_save": false,
    "max_group_level": 1,
    "simplify_group_level": true,
    "default_timezone": "local",
    "preview_size": 64,
    "preview_precision": 1.5
    ```


### ExifTool options

- default:
    ```
    "-j": "auto",
    "-s": "auto",
    "-b": "auto",
    "-G:0:1:2:3:4:5:6:7": "forced",
    "-sep ;": "forced",
    "-n": "on",
    "-a": "on",
    "-U": "on",
    "-P": "on",
    "-overwrite_original": "on"
    ```
- GUI for ExifTool options is under development