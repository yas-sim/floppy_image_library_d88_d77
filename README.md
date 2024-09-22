# Floppy disk image manipulation library
(WIP)  
This libray is intended to be used for manipulating the floppy disk images for emulators.

### 'FD_IMAGE' and its derivative classes
This class represents a floppy disk image file that may contain multiple floppy disk information.
|Name|Description|Note|
|---|---|---|
|`self.images[]`|List of `FLOPPY_DISK` objects||


### 'FLOPPY_DISK' and derivative classes
This class represents the data of a single floppy disk.
|Name|Description|Note|
|---|---|---|
|`self.optional_args['disk_name']`|Disk name|16 characters max|
|`self.optional_args['write_protect']`|Write protect flag|0x00: No protect<br>0x10: Write protected|
|`self.optional_args['disk_type']`|Disk type|0x00: 2D<br>0x10: 2DD<br>0x20: 2HD|
|`self.optional_args['disk_size']`|Size of the image data||
|`self.optional_args['track_table'][]`|Offset to the track data from the top of the image data. 0 ~ 163 track.||


### Track data
|Name|Description|Note|
|---|---|---|
|`track_size`|Track size|Size of the track_data|
|`track_data`|Track data|The track data consists of multiple sector data. The sector data are simply concatenated back to back. (bytearray)|
|`sectors[]`|List of 'Sector data'||


### Sector data
|Name|Description|Note|
|---|---|---|
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
