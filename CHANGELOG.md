# Fuse Sublime package 1.2.3

## New features
* Suggestion matching should be more aggressive now, omitting more false positives.
* Added experimental feature for folding attributes by namespace. For instance all ux: attributes such as ```ux:Name``` are folded into the single suggestion ```ux:``` until the ```:``` has been typed past. This feature is currently opt-in and can be enabled with the setting ```fuse_ux_attrib_folding```.