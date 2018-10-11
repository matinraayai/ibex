import math
import time
import random
import struct

from ibex.utilities import dataIO
from ibex.utilities.constants import *
from ibex.transforms import seg2gold
from ibex.cnns.skeleton.util import SkeletonCandidate


# save the candidate files for the CNN
def SaveCandidates(output_filename, candidates):
    random.shuffle(candidates)
    ncandidates = len(candidates)

    # write all candidates to the file
    with open(output_filename, 'wb') as fd:
        fd.write(struct.pack('q', len(candidates)))

        # add every candidate to the binary file
        for candidate in candidates:
            # get the labels for this candidate
            label_one = candidate.labels[0]
            label_two = candidate.labels[1]

            # get the location of this candidate
            position = candidate.location
            ground_truth = candidate.ground_truth

            # write this candidate to the evaluation candidate list
            fd.write(struct.pack('qqqqq?', label_one, label_two, position[IB_Z], position[IB_Y], position[IB_X], ground_truth))          



def GenerateEdges(prefix, maximum_distance):
    # read in the segmentation and gold datasets to find a mapping
    segmentation = dataIO.ReadSegmentationData(prefix)
    gold = dataIO.ReadGoldData(prefix)
    resolution = dataIO.Resolution(prefix)
    
    # get the mapping from segmentation to gold
    seg2gold_mapping = seg2gold.Mapping(segmentation, gold)

    start_time = time.time()

    skeletons = dataIO.ReadSkeletons(prefix)

    endpoints = [ skeleton.Endpoints2Array() for skeleton in skeletons.skeletons ]


    # keep track of all the potential locations
    midpoints = []
    ground_truths = []
    labels = []

    # go through all pairs of skeletons and find endpoints within maximum_distance
    max_label = len(endpoints)
    for is1 in range(max_label):
        for is2 in range(is1 + 1, max_label):
            # go through all endpoints in segment one
            for endpoint_one in endpoints[is1]:
                for endpoint_two in endpoints[is2]:
                    zdiff = resolution[IB_Z] * (endpoint_two[IB_Z] - endpoint_one[IB_Z])
                    ydiff = resolution[IB_Y] * (endpoint_two[IB_Y] - endpoint_one[IB_Y])
                    xdiff = resolution[IB_X] * (endpoint_two[IB_X] - endpoint_one[IB_X])

                    distance = math.sqrt(zdiff * zdiff + ydiff * ydiff + xdiff * xdiff)

                    if (distance < maximum_distance):
                        midpoint = ((endpoint_two[IB_Z] + endpoint_one[IB_Z]) / 2, (endpoint_two[IB_Y] + endpoint_one[IB_Y]) / 2, (endpoint_two[IB_X] + endpoint_one[IB_X]) / 2)
                        ground_truth = (seg2gold_mapping[is1] == seg2gold_mapping[is2])
                        if not seg2gold_mapping[is1] and not seg2gold_mapping[is2]:
                            ground_truth = -1

                        midpoints.append(midpoint)
                        ground_truths.append(ground_truth)
                        labels.append((is1, is2))

    # create list of candidates
    positive_candidates = []
    negative_candidates = []
    undetermined_candidates = []

    for iv in range(len(midpoints)):
        if ground_truths[iv] == -1: 
            undetermined_candidates.append(SkeletonCandidate(labels[iv], midpoints[iv], ground_truths[iv]))
        elif ground_truths[iv] == 0: 
            negative_candidates.append(SkeletonCandidate(labels[iv], midpoints[iv], ground_truths[iv]))
        elif ground_truths[iv] == 1: 
            positive_candidates.append(SkeletonCandidate(labels[iv], midpoints[iv], ground_truths[iv]))

    print 'Number positive edges {}'.format(len(positive_candidates))
    print 'Number negative edges {}'.format(len(negative_candidates))
    print 'Number undetermined edges {}'.format(len(undetermined_candidates))

    # save positive and negative candidates separately
    positive_filename = 'features/skeleton/{}-{}nm-positive.candidates'.format(prefix, maximum_distance)
    negative_filename = 'features/skeleton/{}-{}nm-negative.candidates'.format(prefix, maximum_distance)
    undetermined_filename = 'features/skeleton/{}-{}nm-undetermined.candidates'.format(prefix, maximum_distance)
        
    SaveCandidates(positive_filename, positive_candidates)
    SaveCandidates(negative_filename, negative_candidates)
    SaveCandidates(undetermined_filename, undetermined_candidates)


# import math
# import numpy as np
# import random
# import struct
# from numba import jit
# import time

# from ibex.utilities.constants import *
# from ibex.utilities import dataIO
# from ibex.transforms import seg2seg, seg2gold
# from ibex.cnns.skeleton.util import SkeletonCandidate
# from ibex.data_structures import unionfind
# from ibex.evaluation import comparestacks



# # save the candidate files for the CNN
# def SaveCandidates(output_filename, candidates):
#     random.shuffle(candidates)
#     ncandidates = len(candidates)

#     # write all candidates to the file
#     with open(output_filename, 'wb') as fd:
#         fd.write(struct.pack('i', len(candidates)))

#         # add every candidate to the binary file
#         for candidate in candidates:
#             # get the labels for this candidate
#             label_one = candidate.labels[0]
#             label_two = candidate.labels[1]

#             # get the location of this candidate
#             position = candidate.location
#             ground_truth = candidate.ground_truth

#             # write this candidate to the evaluation candidate list
#             fd.write(struct.pack('qqqqq?', label_one, label_two, position[IB_Z], position[IB_Y], position[IB_X], ground_truth))          



# @jit(nopython=True)
# def FindNeighboringCandidates(segmentation, centroid, candidates, maximum_distance, world_res):
#     # useful variables
#     zres, yres, xres = segmentation.shape
#     max_label = np.amax(segmentation) + 1

#     # get the radii and label for this centroid
#     radii = np.int64((maximum_distance / world_res[IB_Z], maximum_distance / world_res[IB_Y], maximum_distance / world_res[IB_X]))
#     label = segmentation[centroid[IB_Z],centroid[IB_Y],centroid[IB_X]]

#     # iterate through all the pixels close to the centroid
#     for iz in range(centroid[IB_Z]-radii[IB_Z], centroid[IB_Z]+radii[IB_Z]+1):
#         if iz < 0 or iz > zres - 1: continue
#         for iy in range(centroid[IB_Y]-radii[IB_Y], centroid[IB_Y]+radii[IB_Y]+1):
#             if iy < 0 or iy > yres - 1: continue
#             for ix in range(centroid[IB_X]-radii[IB_X], centroid[IB_X]+radii[IB_X]+1):
#                 if ix < 0 or ix > xres - 1: continue
#                 # skip extracellular and locations with the same label
#                 if not segmentation[iz,iy,ix]: continue
#                 if segmentation[iz,iy,ix] == label: continue

#                 # get the distance from the centroid
#                 distance = math.sqrt((world_res[IB_Z] * (centroid[IB_Z] - iz)) * (world_res[IB_Z] * (centroid[IB_Z] - iz))  + (world_res[IB_Y] * (centroid[IB_Y] - iy)) * (world_res[IB_Y] * (centroid[IB_Y] - iy)) + (world_res[IB_X] * (centroid[IB_X] - ix)) * (world_res[IB_X] * (centroid[IB_X] - ix)))
#                 if distance > maximum_distance: continue

#                 # is there already a closer location
#                 neighbor_label = segmentation[iz,iy,ix]
#                 candidates.add(neighbor_label)



# # generate features for this prefix
# def GenerateFeatures(prefix, threshold, maximum_distance, network_distance, endpoint_distance, topology):
#     start_time = time.time()

#     # read in the relevant information
#     segmentation = dataIO.ReadSegmentationData(prefix)
#     gold = dataIO.ReadGoldData(prefix)
#     assert (segmentation.shape == gold.shape)
#     zres, yres, xres = segmentation.shape

#     # remove small connceted components
#     thresholded_segmentation = seg2seg.RemoveSmallConnectedComponents(segmentation, threshold=threshold).astype(np.int64)
#     max_label = np.amax(segmentation) + 1
    
#     # get the grid size and the world resolution
#     grid_size = segmentation.shape
#     world_res = dataIO.Resolution(prefix)

#     # get the radius in grid coordinates
#     radii = np.int64((maximum_distance / world_res[IB_Z], maximum_distance / world_res[IB_Y], maximum_distance / world_res[IB_X]))
#     network_radii = np.int64((network_distance / world_res[IB_Z], network_distance / world_res[IB_Y], network_distance / world_res[IB_X]))
    
#     # get all of the skeletons
#     if topology: skeletons, endpoints = dataIO.ReadTopologySkeletons(prefix, thresholded_segmentation)
#     else: skeletons, _, endpoints = dataIO.ReadSWCSkeletons(prefix, thresholded_segmentation)
    
#     # get the set of all considered pairs
#     endpoint_candidates = [set() for _ in range(len(endpoints))]
#     for ie, endpoint in enumerate(endpoints):
#         # extract the region around this endpoint
#         label = endpoint.label
#         centroid = endpoint.GridPoint()

#         # find the candidates near this endpoint
#         candidates = set()
#         candidates.add(0)
#         FindNeighboringCandidates(thresholded_segmentation, centroid, candidates, maximum_distance, world_res)

#         for candidate in candidates:
#             # skip extracellular
#             if not candidate: continue
#             endpoint_candidates[ie].add(candidate)

#     # get a mapping from the labels to indices in skeletons and endpoints
#     label_to_index = [-1 for _ in range(max_label)]
#     for ie, skeleton in enumerate(skeletons):
#         label_to_index[skeleton.label] = ie 

#     # begin pruning the candidates based on the endpoints
#     endpoint_pairs = {}

#     # find the smallest pair between endpoints
#     smallest_distances = {}
#     midpoints = {}

#     for ie, endpoint in enumerate(endpoints):
#         label = endpoint.label
#         for neighbor_label in endpoint_candidates[ie]:
#             smallest_distances[(label,neighbor_label)] = endpoint_distance + 1
#             smallest_distances[(neighbor_label,label)] = endpoint_distance + 1

#     for ie, endpoint in enumerate(endpoints):
#         # get the endpoint location
#         label = endpoint.label

#         # go through all currently considered endpoints
#         for neighbor_label in endpoint_candidates[ie]:
#             for neighbor_endpoint in skeletons[label_to_index[neighbor_label]].endpoints:
#                 # get the distance
#                 deltas = endpoint.WorldPoint(world_res) - neighbor_endpoint.WorldPoint(world_res)
#                 distance = math.sqrt(deltas[IB_Z] * deltas[IB_Z] + deltas[IB_Y] * deltas[IB_Y] + deltas[IB_X] * deltas[IB_X])
                
#                 if distance < smallest_distances[(label, neighbor_label)]:
#                     midpoint = (endpoint.GridPoint() + neighbor_endpoint.GridPoint()) / 2

#                     # find the closest pair of endpoints
#                     smallest_distances[(label,neighbor_label)] = distance
#                     smallest_distances[(neighbor_label,label)] = distance

#                     # add to the dictionary
#                     endpoint_pairs[(label, neighbor_label)] = (endpoint, neighbor_endpoint)
#                     endpoint_pairs[(neighbor_label, label)] = (neighbor_endpoint, endpoint)

#                     midpoints[(label,neighbor_label)] = midpoint
#                     midpoints[(neighbor_label,label)] = midpoint


#     # create list of candidates
#     positive_candidates = []
#     negative_candidates = []
#     undetermined_candidates = []

#     for ie, match in enumerate(endpoint_pairs):
#         print '{}/{}'.format(ie, len(endpoint_pairs))
#         endpoint_one = endpoint_pairs[match][0]
#         endpoint_two = endpoint_pairs[match][1]

#         label_one = endpoint_one.label
#         label_two = endpoint_two.label

#         if label_two > label_one: continue
        
#         # extract a bounding box around this midpoint
#         midz, midy, midx = midpoints[(label_one,label_two)]

#         zmin = max(0, midz - network_radii[IB_Z])
#         ymin = max(0, midy - network_radii[IB_Y])
#         xmin = max(0, midx - network_radii[IB_X])
#         zmax = min(zres - 1, midz + network_radii[IB_Z] + 1)
#         ymax = min(yres - 1, midy + network_radii[IB_Y] + 1)
#         xmax = min(xres - 1, midx + network_radii[IB_X] + 1)

#         extracted_segmentation = segmentation[zmin:zmax,ymin:ymax,xmin:xmax]
#         extracted_gold = gold[zmin:zmax,ymin:ymax,xmin:xmax]

#         extracted_seg2gold_mapping = seg2gold.Mapping(extracted_segmentation, extracted_gold, match_threshold=0.70, nonzero_threshold=0.40)

#         if label_one > extracted_seg2gold_mapping.size: continue
#         if label_two > extracted_seg2gold_mapping.size: continue

#         gold_one = extracted_seg2gold_mapping[label_one]
#         gold_two = extracted_seg2gold_mapping[label_two]

#         ground_truth = (gold_one == gold_two)

#         candidate = SkeletonCandidate((label_one, label_two), midpoints[(label_one,label_two)], ground_truth)

#         if not extracted_seg2gold_mapping[label_one] or not extracted_seg2gold_mapping[label_two]: undetermined_candidates.append(candidate)
#         elif ground_truth: positive_candidates.append(candidate)
#         else: negative_candidates.append(candidate)

#     # save positive and negative candidates separately
#     positive_filename = 'features/skeleton/{}-{}-{}nm-{}nm-{}nm-positive.candidates'.format(prefix, threshold, maximum_distance, endpoint_distance, network_distance)
#     negative_filename = 'features/skeleton/{}-{}-{}nm-{}nm-{}nm-negative.candidates'.format(prefix, threshold, maximum_distance, endpoint_distance, network_distance)
#     undetermined_filename = 'features/skeleton/{}-{}-{}nm-{}nm-{}nm-undetermined.candidates'.format(prefix, threshold, maximum_distance, endpoint_distance, network_distance)
    
#     SaveCandidates(positive_filename, positive_candidates)
#     SaveCandidates(negative_filename, negative_candidates)
#     SaveCandidates(undetermined_filename, undetermined_candidates)

#     print 'Positive candidates: {}'.format(len(positive_candidates))
#     print 'Negative candidates: {}'.format(len(negative_candidates))
#     print 'Undetermined candidates: {}'.format(len(undetermined_candidates))

#     # perform some tests to see how well this method can do
#     #max_value = np.amax(segmentation) + 1
#     #union_find = [unionfind.UnionFindElement(iv) for iv in range(max_value)]
    
#     # iterate over all collapsed edges
#     #for candidate in positive_candidates:
#     #    label_one, label_two = candidate.labels
#     #    unionfind.Union(union_find[label_one], union_find[label_two])
    
#     # create a mapping for the labels
#     #mapping = np.zeros(max_value, dtype=np.int64)
#     #for iv in range(max_value):
#     #    mapping[iv] = unionfind.Find(union_find[iv]).label
   
#     #segmentation = seg2seg.MapLabels(segmentation, mapping)
#     #comparestacks.CremiEvaluate(segmentation, gold, dilate_ground_truth=1, mask_ground_truth=True, filtersize=0)