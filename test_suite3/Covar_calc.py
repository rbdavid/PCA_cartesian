#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python
##!/mnt/lustre_fs/users/mjmcc/apps/python2.7/bin/python
# ----------------------------------------
# USAGE:
# ----------------------------------------


# ----------------------------------------
# PREAMBLE:
# ----------------------------------------

import sys
import numpy as np
from numpy.linalg import *
import MDAnalysis
from MDAnalysis.analysis.align import *
from distance_functions import *

# ----------------------------------------
# VARIABLE DECLARATION
# ----------------------------------------

pdb_file = sys.argv[1]
traj_loc = sys.argv[2]
start = int(sys.argv[3])
end = int(sys.argv[4])
avg_pdb = sys.argv[5]		# Used to align frames to; not to be used average positions due to precision error of positions in PDB format
#avg_dcd = sys.argv[6]

alignment = 'protein and name CA and (resid 20:25 or resid 50:55 or resid 73:75 or resid 90:94 or resid 112:116 or resid 142:147 or resid 165:169 or resid 190:194 or resid 214:218 or resid 236:240 or resid 253:258 or resid 303:307)'
important = 'protein'
#important = 'protein and not resid 0:12'

Functionalize = True
PCA = True

flatten = np.ndarray.flatten
zeros = np.zeros
dot_prod = np.dot
sqrt = np.sqrt
eigen = np.linalg.eig
flush = sys.stdout.flush

# ----------------------------------------
# SUBROUTINES:
# ----------------------------------------

def ffprint(string):
	print '%s' %(string)
	flush()

# ----------------------------------------
# MAIN PROGRAM:
# ----------------------------------------
# INITIATE AND CALCULATE THE IMPORTANT INFORMATION ABOUT THE AVG STRUCTURE
avg = MDAnalysis.Universe(avg_pdb)
#avg = MDAnalysis.Universe(avg_pdb,avg_dcd)
avg_all = avg.select_atoms('all')
avg_align = avg.select_atoms(alignment)
avg_important = avg.select_atoms(important)

avg_all.translate(-avg_align.center_of_mass())
pos0 = avg_align.positions
nRes = avg_important.n_residues
ffprint('Initiated the average structure universe')

# ----------------------------------------
# INITIATE AND CREATE THE IMPORTANT ATOM SELECTIONS FOR THE IMPORTANT UNIVERSE
u = MDAnalysis.Universe(pdb_file)
u_all = u.select_atoms('all')
u_align = u.select_atoms(alignment)
u_important = u.select_atoms(important)

if nRes != u_important.n_residues:
	ffprint('Number of residues do not match between average structure and trajectory universes')
	sys.exit()

ffprint('Initiated the analysis universe')

# COLLECTING NSTEPS DATA... NEED TO ITERATE THROUGH ALL TRAJECTORIES TO COLLECT THIS...
nSteps = 0
while start <= end:
	u.load_new('%s' %(traj_loc))
	nSteps += len(u.trajectory)
	start += 1

ffprint('The number of timesteps to be analyzed is %d.' %(nSteps))
start = int(sys.argv[3])

# ARRAY DECLARATION
allCoord = zeros((nSteps,nRes,3),dtype=np.float64)
avgCoord = zeros((nRes,3),dtype=np.float64)
dist_covar_array = zeros((nRes,nRes),dtype=np.float64)
msd_array = zeros(nRes,dtype=np.float64)

# TRAJECTORY ANALYSIS; COLLECTING THE COM INFO OF EACH RESIDUE OF INTEREST
ffprint('Beginning trajectory analysis')
temp = 0
while start <= end:
	ffprint('Loading trajectory %s' %(start))
	u.load_new('%s' %(traj_loc))
	for ts in u.trajectory:
		u_all.translate(-u_align.center_of_mass())
		R,d = rotation_matrix(u_align.positions,pos0)
		u_all.rotate(R)
		for i in range(nRes):
			allCoord[temp,i,:] = u_important.residues[i].center_of_mass()		# BUG IN ts.frame; will re-zero at the start of the next trajectory...
			avgCoord[i,:] += u_important.residues[i].center_of_mass()
		temp += 1
	start += 1
avgCoord /= nSteps
ffprint('Finished with the trajectory analysis. On to calculating the covariance matrix for residue-residue COM distance.')

# ----------------------------------------
# CALCULATING THE DISTANCE COVAR MATRIX OF RESIDUE RESIDUE PAIRS
for i in range(nSteps):
	temp_array = zeros((nRes,3),dtype=np.float64)
	for res1 in range(nRes):
		temp_array[res1,:] = allCoord[i,res1,:] - avgCoord[res1,:]		# Calculating the delta r for every timestep
		msd_array[res1] += dot_prod(temp_array[res1,:],temp_array[res1,:])		# Sum over all timesteps; 
	for res1 in range(nRes):
		for res2 in range(res1,nRes):
			dist_covar_array[res1,res2] += dot_prod(temp_array[res1,:],temp_array[res2,:])
dist_covar_array /= nSteps
msd_array /= nSteps
ffprint('Finished with filling the distance covariance matrix. On to normalizing the covar array.')

# COMPLETE THE DISTANCE COVAR MATRIX ANALYSIS BY SUBTRACTING OUT THE MEAN AND NORMALIZING BY THE VARIANCE
for res1 in range(nRes):
	for res2 in range(res1,nRes):
		dist_covar_array[res1,res2] /= sqrt(msd_array[res1]*msd_array[res2])	# Normalizing each matrix element by the sqrt of the variance of the positions for res1 and res2
		dist_covar_array[res2,res1] = dist_covar_array[res1,res2]

# OUTPUTING THE DIST COVAR ARRAY
with open('%03d.%03d.dist_covar_matrix.dat' %(int(sys.argv[3]),end),'w') as f:
	np.savetxt(f,dist_covar_array)
ffprint('Printed out the normalized distance covar array.')

# ----------------------------------------
# FUNCTIONALIZING THE DISTANCE CORRELATION MATRIX (FOR USE IN WISP AND VISUALIZATION)
if Functionalize == True:
	ffprint('Beginning to functionalize the distance covar matrix.')
	for res1 in range(nRes):
		for res2 in range(res1,nRes):
			dist_covar_array[res1,res2] = -np.log(np.fabs(dist_covar_array[res1,res2]))
			dist_covar_array[res2,res1] = dist_covar_array[res1,res2]
	
	# OUTPUTING THE DIST COVAR ARRAY
	with open('%03d.%03d.functionalized_dist_covar_matrix.dat' %(int(sys.argv[3]),end),'w') as f:
		np.savetxt(f,dist_covar_array)
else: 
	ffprint('Functionalize != True. Not functionalizing (taking -log(|C_ij|)) the distance covar matrix.')

# ----------------------------------------
# CALCULATING THE CARTESIAN COVAR ARRAY OF RESIDUE RESIDUE PAIRS
ffprint('Beginning the cartesian covariance matrix analysis')
cart_covar_array = zeros((3*nRes, 3*nRes),dtype=np.float64)
cart_all_array = zeros(3*nRes,dtype=np.float64)
cart_avg_array = zeros(3*nRes,dtype=np.float64)
cart_msd_array = zeros(3*nRes,dtype=np.float64)

cart_avg_array = flatten(avgCoord)
for i in range(nSteps):
	cart_all_array = flatten(allCoord[i])	# Each element in allCoord has three components (xyz); to get at the xyz components individually, flatten the first index
	temp_array = zeros(3*nRes,dtype=np.float64)
	for res1 in range(3*nRes):
		temp_array[res1] = cart_all_array[res1] - cart_avg_array[res1]
		cart_msd_array[res1] += temp_array[res1]*temp_array[res1]
	for res1 in range(3*nRes):
		for res2 in range(res1,3*nRes):
			cart_covar_array[res1,res2] += temp_array[res1]*temp_array[res2]

cart_covar_array /= nSteps
cart_msd_array /= nSteps

# COMPLETE THE CARTESIAN COVAR MATRIX ANALYSIS BY SUBTRACTING OUT THE MEAN
ffprint('Normalizing the cartesian covariance matrix using the variance.')
for res1 in range(3*nRes):
	for res2 in range(res1,3*nRes):
		cart_covar_array[res1,res2] /= sqrt(cart_msd_array[res1]*cart_msd_array[res2])
		cart_covar_array[res2,res1] = cart_covar_array[res1,res2]	

# OUTPUTING THE CARTESIAN COVAR ARRAY
with open('%03d.%03d.cart_covar_matrix.dat' %(int(sys.argv[3]),end),'w') as f:
	np.savetxt(f,cart_covar_array)

# ----------------------------------------
# PCA ANALYSIS OF CARTESIAN COVAR ARRAY
if PCA == True:
	ffprint('Beginning PCA analysis of the Cartesian covariance matrix.')
	eigval,eigvec = eigen(cart_covar_array)
	idx = eigval.argsort()[::-1]
	eigval = eigval[idx]
	
	nVec = len(eigvec)
	cumulative_eigval = np.zeros(nVec)
	total_eigval = 0
	for i in range(nVec):
		total_eigval += eigval[i]
		cumulative_eigval[i] = total_eigval
	
	with open('%03d.%03d.cart_pca.eigvalues.dat' %(int(sys.argv[3]),end),'w') as f:
		for i in range(nVec):
			f.write('%f   %f   %f   %f\n' %(eigval[i],eigval[i]/total_eigval,cumulative_eigval[i],cumulative_eigval[i]/total_eigval))
	
	with open('%03d.%03d.cart_pca.eigvectors.dat' %(int(sys.argv[3]),end),'w') as f:
		for i in range(nVec):
			for j in range(nVec):
				f.write('%f   ' %(eigvec[j,i]))		# Writing each vector on one row/line now, instead of the vectors corresponding to columns in the eigvec array...; NOT projecting covar array onto the eigenvectors (do so outside of this damn script)
			f.write('\n')
else:
	ffprint('PCA != True. Not performing a PCA analysis on the Cartesian Covar matrix.')
