# Installation 
## Build
The DockerFile assumes input data (image.nii.gz,lungs.nii.gz,central_vessels.nii.gz) is in a local directory `./data/`.

```docker build -t segmentvessel .```

## Run container
```docker run -v $LOCAL_DIR:/out/ segmentvessel --i image.nii.gz --segL lungs.nii.gz --segC central_vessels.nii.gz --o /out/out.mhd```
# TODO
- [x] Create docker env
- [x] ITK Vesselness Filter
- [x] ITK Vesselness Segmentation
- [x] Compute vessel volume
- [x] Skeletonisation with scikit-image
- [ ] Determine multiple vessel seed regions where overlap between centralVesselSeg and obtained VesselMask
- [ ] Add argparse parameters for seed regions

# Vessel Segmentation Pipeline
The following the describes the individual steps and corresponding outcomes obtained with individual filter steps.

## Vesselness Filter
The vesselness filter is implementation in class `class VesselSegmentation`, which implements the [ITK blood vessel filter](https://examples.itk.org/src/filtering/imagefeature/segmentbloodvessels/documentation). Alternatively, the vesselness filter can be computed with [Multi-Scale Hessian-Based Measures](https://examples.itk.org/src/nonunit/review/segmentbloodvesselswithmultiscalehessianbasedmeasure/documentation). The output of this filter was multiplied with the provided (binarised) lung mask. See below for an obtained visualisation with ParaView 5.9.1.

![vesselnessFilter](https://user-images.githubusercontent.com/1218950/220034429-887adee7-47ca-468d-a66a-160a27f5120b.png)

## Vesselness Filter Mask
The vesselness fiter volume was binarised by a applying with a fixed threshold(50). Alternatively, one could use [tresholding heurisitics](https://examples.itk.org/src/filtering/thresholding/demonstratethresholdalgorithms/documentation) (Otsu, Triangle).

![vesselMaskInit](https://user-images.githubusercontent.com/1218950/220034528-059912e3-dd96-4f4a-9d9f-2506c7f4b13f.png)

## Vessel Mask Refined with Region Growing
Simple region growing implemented in `class VesselRegionGrowing` was used to refine the initial vessel mask to remove image noise. 

![vesselMaskRefined](https://user-images.githubusercontent.com/1218950/220034735-874e1a5a-21bf-437d-bbc8-c8c9cc991428.png)

### Volume of the obtained mask
Volume of blood vessel mask: 85.14 mL or 85138.74 mm^3

Volume of lung mask: 4046.68 mL or 4046679.93 mm^3

## Vessel Mask Skeletonization
Skeletonization is implemented in `class VesselSkeleton`, a wrapper for Scikit-image method `skeletonize_3d`.

![vesselSkeleton](https://user-images.githubusercontent.com/1218950/220034986-542bd0e3-3f46-4703-911c-d6029a76cd85.png)

## Artery / Vein Separation
A crude separation of vessels into arteries and veins was obtained by using `class VesselRegionGrowing` with a seed either placed in the green or red area of the central vessel segmentation. The resulting individual segmentations were combined into one segmentation display below in ParaView 5.9.1.  
![ArteryVeinSeparation](https://user-images.githubusercontent.com/1218950/220035084-1cf84c2f-ca9a-41f0-b530-08327971547a.png)
