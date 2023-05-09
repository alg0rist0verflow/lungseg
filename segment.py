import itk
from skimage.morphology import skeletonize_3d
import numpy as np
import argparse
import pdb

class Segmentation:

    def __init__(self, segmentationFilename, LowerThreshold=1, UpperThreshold=2) -> None:
        self.segmentation = itk.imread(segmentationFilename)
        maskFilter = itk.BinaryThresholdImageFilter.New(
            self.segmentation,
            LowerThreshold=LowerThreshold,
            UpperThreshold=UpperThreshold,
            InsideValue=1,
            OutsideValue=0
        )
        maskFilter.Update()
        self.mask = maskFilter.GetOutput()

    def Segmentation(self):
        return self.segmentation

    def Mask(self, castType=None):
        if castType:   
            cast_filter = itk.CastImageFilter[itk.Image[itk.UC, 3], castType].New()
            cast_filter.SetInput(self.mask)
            cast_filter.Update()
            return cast_filter.GetOutput()

        return self.mask

class VesselSegmentation:

    def __init__(self, img, mask, sigma=1.0, alpha1=.5, alpha2=2.0, thr=50) -> None:
        self.img = img
        self.mask = mask
        self.sigma = sigma
        self.alpha1 = alpha1
        self.alpha2 = alpha2
        self.thr = thr

    def computeVesselnessSegmentation(self, prefixFilename=None):
        hessianImg = itk.HessianRecursiveGaussianImageFilter.New(self.img, sigma=self.sigma)
        vesselnessFilter = itk.Hessian3DToVesselnessMeasureImageFilter[itk.ctype("float")].New()
        vesselnessFilter.SetInput(hessianImg)
        vesselnessFilter.SetAlpha1(self.alpha1)
        vesselnessFilter.SetAlpha2(self.alpha2)
        vesselnessImg = vesselnessFilter.GetOutput()
        maskedVesselNessFilter = itk.MultiplyImageFilter.New(vesselnessImg, self.mask)
        maskedVesselNessImg = maskedVesselNessFilter.GetOutput()
        if prefixFilename:
            itk.imwrite(maskedVesselNessImg, prefixFilename+'vesselness.mhd')

        #Threshold the vesselness image to obtain a binary mask of the vessels
        threshold_filter = itk.BinaryThresholdImageFilter[itk.Image[itk.F, 3], itk.Image[itk.UC, 3]].New()
        threshold_filter.SetInput(maskedVesselNessImg)
        threshold_filter.SetLowerThreshold(self.thr)
        threshold_filter.SetInsideValue(1)
        threshold_filter.SetOutsideValue(0)
        
        if prefixFilename:
            itk.imwrite(threshold_filter, prefixFilename+'vessel_mask.mhd')

        return threshold_filter.GetOutput()

class VesselRegionGrowing:

    def __init__(self, lungVesselSeg, centralVesselSeg, replaceVal, connectivity=None) -> None:
        self.lungVesselSeg = lungVesselSeg
        self.centralVesselSeg = centralVesselSeg
        self.replaceVal = replaceVal
        self.connectivity = connectivity

    def computeVesselRegionGrowing(self, seed=[260,277,160]):
        vesselMaskPlusCentralVesselsFilter = itk.MaximumImageFilter.New(self.lungVesselSeg, self.centralVesselSeg.Mask())
        seedPoint = itk.Index[3]()
        seedPoint[0] = seed[0]
        seedPoint[1] = seed[1]
        seedPoint[2] = seed[2]
        vesselFilter = itk.ConnectedThresholdImageFilter.New(vesselMaskPlusCentralVesselsFilter.GetOutput())
        if self.connectivity:
            vesselFilter.SetConnectivity(self.connectivity)

        vesselFilter.SetSeed(seedPoint)
        vesselFilter.SetLower(1)
        vesselFilter.SetReplaceValue(self.replaceVal)
        vesselFilter.Update()
        vesselImg = vesselFilter.GetOutput()
        return vesselImg
        
class VesselSkeleton:

    def __init__(self, vesselMask) -> None:
        self.vesselMask = vesselMask

    def skeletonize(self, prefixFilename=None):
        skeleton = skeletonize_3d(self.vesselMask)
        skeletonImg = itk.GetImageFromArray(skeleton)
        skeletonImg.CopyInformation(self.vesselMask)
        if prefixFilename:
            itk.imwrite(skeletonImg, prefixFilename+"skeleton.mhd")
        return skeletonImg

def computeMaskSize(mask):
    spacing = mask.GetSpacing()
    voxel_size_mm = spacing[0] * spacing[1] * spacing[2]
    array_view = itk.array_view_from_image(mask)
    volumeInMM3 = float(array_view.sum()) * voxel_size_mm
    return volumeInMM3
     
def main():
    parser = argparse.ArgumentParser(description='Segment a volume.')
    parser.add_argument('--i', help='Input image file name.', default="./data/image.nii.gz")
    parser.add_argument('--segL', help='Mask image file name.', default="./data/lungs.nii.gz")
    parser.add_argument('--segC', help='Mask image file name.', default="./data/central_vessels.nii.gz")
    parser.add_argument('--o', help='Output image file name.', default="./out/out.mhd")
    parser.add_argument('--sigma', type=float, default=1.0)
    parser.add_argument('--alpha1', type=float, default=0.5)
    parser.add_argument('--alpha2', type=float, default=2.0)
    parser.add_argument('--thr', type=float, default=50)
    args = parser.parse_args()
    prefixFilename = args.o.replace(".mhd", "_").replace(".nii.gz", "_")
    inputImg= itk.imread(args.i)
    lungSegmentation = Segmentation(args.segL)
    centralVesselSegmentation = Segmentation(args.segC)
    vesselSeg = VesselSegmentation(inputImg, lungSegmentation.Mask(castType=itk.Image[itk.F, 3]), 
        sigma=args.sigma, alpha1=args.alpha1, alpha2=args.alpha2, thr=args.thr)

    vesselMask = vesselSeg.computeVesselnessSegmentation(prefixFilename=prefixFilename)
    vesselRegionGrowing = VesselRegionGrowing(vesselMask, centralVesselSegmentation, replaceVal=1)
    vesselSegmentation = vesselRegionGrowing.computeVesselRegionGrowing(seed=[260,277,160])
    maskedVesselFilter = itk.MultiplyImageFilter.New(vesselSegmentation, lungSegmentation.Mask())
    vesselMaskRefined = maskedVesselFilter.GetOutput()
    itk.imwrite(vesselMaskRefined, prefixFilename+"vessel_mask_refined.mhd")
    ### Compute the size of the mask
    volumeInMM3 = computeMaskSize(vesselMaskRefined)
    volumeInCML = volumeInMM3 / 1000.0
    print("Volume of blood vessel mask: {} mL or {} mm^3".format(np.round(volumeInCML,2), np.round(volumeInMM3,2)))
    volumeInMM3 = computeMaskSize(lungSegmentation.Mask())
    volumeInCML = volumeInMM3 / 1000.0
    print("Volume of lung mask: {} mL or {} mm^3".format(np.round(volumeInCML,2), np.round(volumeInMM3,2)))
    # Get a NumPy array view from the image
    vesselSkeleton = VesselSkeleton(vesselMaskRefined).skeletonize(prefixFilename=prefixFilename)
    # Use skeleton and central vessel mask to separate in arteries and veins
    centralArteriesSegmenation = Segmentation(args.segC, LowerThreshold=1, UpperThreshold=1)
    centralVeinsSegmenation = Segmentation(args.segC, LowerThreshold=2, UpperThreshold=2)
    veinMask = VesselRegionGrowing(vesselSkeleton, centralVeinsSegmenation, replaceVal=1, connectivity=1).computeVesselRegionGrowing(seed=[260,277,160])
    artMask = VesselRegionGrowing(vesselSkeleton, centralArteriesSegmenation, replaceVal=2, connectivity=1).computeVesselRegionGrowing(seed=[311,220,160])
    combinedSeg = itk.AddImageFilter.New(veinMask,artMask)
    itk.imwrite(combinedSeg.GetOutput(), prefixFilename+"final_combined_seg.mhd")
    itk.imwrite(combinedSeg.GetOutput(), prefixFilename+"final_combined_seg.nii.gz")

# create main function
if __name__ == "__main__":
    main()

# create Dockerfile to run this code
# FROM python:3.8-slim-buster




