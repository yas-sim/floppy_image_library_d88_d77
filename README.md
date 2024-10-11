# Floppy disk image manipulation library
(WIP)  
This libray is intended to be used for manipulating the floppy disk images for emulators.  
Initial target is to support D88/D77 floppy disk image format.  

NOTICE: CLI commands and file system only supports Fujitsu FM-7 series disk BASIC foromat disks.   

----------------------------

## CLI commands:

### `fmdir.py`
**Description**: Show directory entries of an FM-7 DISK BASIC disk in D88/D77 image file.  

```sh
options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  D88/D77 image file name
  -n IMAGE_NUMBER, --image_number IMAGE_NUMBER
                        Specify target image number (if the image file contains multiple images). Default=0
  --original            Display the original file name
  -v, --verbose         Verbose flag
```

Command line examples:
```sh
python fmdir.py -f fb3l2.d77 -n 0
  0 DFMCD    2 B S   0    2
  1 MCOPY    2 B S   1    4
  2 SYSDSK   0 B S   2    6
  3 VOLCOPY  0 B S   3    5
  4 AUTOUTY  0 B S   4    3
  5 PFDEF    0 B S   5    9
  6 SYSUTY   0 B S   7   39
  :   :       :
 34 TEST     1 A S  68    3
 35 WOMAN    1 A S  69   37
 36 KOMACHI  1 A S  74   48
 ```


### `fmread.py`

**Description**: Read a file from an FM-7 DISK BASIC disk in D88/D77 image file.  

```sh
options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  D88/D77 image file name
  -n IMAGE_NUMBER, --image_number IMAGE_NUMBER
                        Specify target image number (if the image file contains
                        multiple images). Default=0
  -s SOURCE, --source SOURCE
                        Source file name in the image file to read.
  -i INDEX, --index INDEX
                        Directory index number to specify the target file to read.
  -d DESTINATION, --destination DESTINATION
                        Destination (destination) file name. When omitted, the source
                        file name and file attributes are used to generate the
                        destination file name.
  -v, --verbose         Verbose flag
  --decode_ir           File contents decode flag. If this flag is set, BASIC IR code
                        will be decoded and stored as plain text source file.
  ```
Command line examples: 

Read a file from the image #0 in '`image.d88`' and write it to '`GAME.dat`'. The file extension represents the source file attributes. The final output file name would be something like '`game.dat.0BS`'.
```sh
python fmread.py -f image.d88 -n 0 -s GAME -d GAME.dat
```
Read a file from the image #0 in '`image.d77`'. The output file name will be generated based on the read file name and its attributes. The final output file name would be something like '`GAME.0BS`'.
```sh
python fmread.py -f image.d88 -n 0 -i 1
```

### `fmwrite.py`  
**Description**: Write a file to an FM-7 DISK BASIC disk in D88/D77 image file.  

```sh
options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  D88/D77 image file name
  -n IMAGE_NUMBER, --image_number IMAGE_NUMBER
                        Specify target image number (if the image file contains multiple images). Default=0
  -s SOURCE, --source SOURCE
                        Source file name to be written to the image file.
  -v, --verbose         Verbose flag
```

Command line examples:
Write '`GAME.0AS` file to the `test.d88` image file.
```sh
python fmwrite.py -f test.d88 -s GAME.0AS
```

### `fmmakedisk.py`  

Create a D88 new image file. The new image file contains only one disk image. The disk image will be formatted in FM-7 DISK BASIC format.  
```sh
options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  D88/D77 image file name
  -v, --verbose         Verbose flag
  ```

----------------------------

## Library API document  
You can find a simple API document [here](./html_docs/index.html).

----------------------------
### 'FD_IMAGE' and its derivative classes
This class represents a floppy disk image file that may contain multiple floppy disk information.
|Name|Description|Note|
|---|---|---|
|`self.images[]`|List of `FLOPPY_DISK` objects||


### 'FLOPPY_DISK' and derivative classes
This class represents the data of a single floppy disk.
|Name|Description|Note|
|---|---|---|
|`self.disk_name`|Disk name|16 characters max|
|`self.write_protect`|Write protect flag|0x00: No protect<br>0x10: Write protected|
|`self.disk_type`|Disk type|0x00: 2D<br>0x10: 2DD<br>0x20: 2HD|
|`self.tracks[[],[],[],...]`|Track data|A list consists of lists of 'sector data'|



### Sector data
|Name|Description|Note|
|---|---|---|
|`sect_idx`|Index number of the sector|Sector number in a track. Starts with 0.|
|`C`|Cylinder #||
|`H`|Head #||
|`R`|Sector ID||
|`N`|Sector size|0:128, 1:256, 2:512, 3:1024|
|`num_sectors`|Number of sectors in the track. In the D88 format, every sector contains this num_sectors data (although it's redundant).|
|`density`|Data density|0x00:Double<br>0x40:Single|
|`data_mark`|Data mark|0x00: Normal data mark<br>0x10: Deleted data mark|
|`status`|Status|0x00: No error<br>0x10: No error (DDM)<br>0a0: ID CRC error<br>0xb0: Data CRC error<br>0xe0: No address mark<br>0xf0: No data mark|
|`data_size`|Size of the sector data||
|`sect_data[]`|Actual sector data (bytearray)|


-------------------------------------------

## D88 Image Format Specification

All numerical data are stored in little-endien byte order.

|Section Name|Description|Note|
|---|---|---|
|Header|Header|Contains disk attributes (0x02b0 bytes)|
|Track data[]|Array of track data|D88 format supports 164 tracks|

### D88 Image Format Header Structure  
Header size = 0x20 + 0x04 * 164 = 0x2b0
|Offset|Size|Description|Note|
|---|---|---|---|
|0x00|0x11|Disk image name|Ascii code. The last byte (17th) must be 0x00|
|0x11|0x09|Padding|Filled with 0x00|
|0x1a|0x01|Write protect flag|0x00:Not protected<br>0x10:Write protected|
|0x1b|0x01|Disk density|0x00:2D<br>0x10:2DD<br>0x20:2HD|
|0x1c|0x04|Disk image size|This includes header and all track data.|
|0x20|0x04[164]|Track offset table|Offset to the track data from the top of the image data. This table contains offset for 164 track data|

### D88 Track Data Structure  
|Offset|Size|Descriptor|Note|
|---|---|---|---|
|0x00|0x01|C||
|0x01|0x01|H||
|0x02|0x01|R||
|0x03|0x01|N||
|0x04|0x02|Number of sectors in this track||
|0x06|0x01|Encoding density|0x00:MFM (double)<br>0x40:FM (single)|
|0x07|0x01|Data Mark|0x00:Normal data mark<br>0x10:Deleted data mark|
|0x08|0x01|Read status|0x00:No error<br>0x10:No error(DDM)<br>0xa0:ID CRC error<br>0xb0:Data CRC error<br>0xe0:No address mark<br>0xf0:No data mark|
|0x09|0x05|Padding||
|0x0e|0x02|Data size of this sector||
|0x10|(Data size of this sector)|Sector data||

--------------------------------------------------------------

## F-BASIC disk map
In this table, track = C*2+H. The sector number starts from 1 (the 1stsector on a track is 1).  
|track|sector|description|note|
|---|---|---|---|
|0|1-2|IPL|Initial program loader|
|0|3|ID|Disk identification data. The sector start with 'SYS'.|
|0|4-16|Reserve||
|1|1-16|Disk BASIC code||
|2|1|FAT||
|2|2-3|Reserve||
|2|4-16|Directory||
|3|1-16|Directory||

### Cluster in F-BASIC  
F-BASIC manages data in a unit of cluster. Each cluster consists of 8 sectors. The cluster 0 starts from track 4 (C=2, H=0).

### FAT in F-BASIC
One byte in the FAT represents a cluster. The FAT starts from 6th byte in the FAT (The top 5 bytes are reserved).

|offset|size|description|note|
|----|----|----|----|
|0x00|0x05|Reserve||
|0x05|0x98|FAT table|For 152 clusters.<br>0x00-0x97: In-use. Indicating next cluster number.<br>0xc0-0xc7: In-use, and indicating the last cluster of the cluster chain. The lower 4-bits represents the number of sectores used in the last cluster.<br>0xfd: No sectors are used in this cluster.<br>0xfe: Reserved for system use.<br>0xff: Not in-use.|

### Directory entry in F-BASIC  

A directory entry consists of 32 bytes of data.  
When a file is deleted, the top of the file name is set to 0x00, and the used clusters are freed (FAT chain is cleard with 0xff).
|offset|size|description|note|
|----|----|----|----|
|0x00|0x08|File name||
|0x08|0x03|reserved||
|0x0b|0x01|File type|0x00:BASIC text<br>0x01:BASIC data<br>0x02:Machine code|
|0c0c|0x01|ASCII flag|0x00:Binary<br>0xff:ASCII|
|0c0d|0x01|Random access flag|0x00:Sequential<br>0xff:Random access|
|0x0e|0x01|The first cluster number||
|0x0f|0x11|reserved|

-----------------------------
## Bin list
- ☑ Image write back
- ☑ New image creation
- ☑ File attribute check on write_file
- ☑ Disk full detection on wite_file
- ☐ Sector read error handling
- ☑ File access by dir_idx
- ☐ File access CLI commands
- ☐ Motorola-S decoding encoding
- ☑ Image serialization
- ☑ Image deserialization
- ☐ GUI ?
