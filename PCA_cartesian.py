#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python
##!/mnt/lustre_fs/users/mjmcc/apps/python2.7/bin/python
# ----------------------------------------
# USAGE:


# ----------------------------------------
# PREAMBLE:

import sys
import numpy as np
from numpy.linalg import *
import MDAnalysis
from MDAnalysis.analysis.align import *
from distance_functions import *

# ----------------------------------------
# VARIABLE DECLARATION

pdb_file = sys.argv[1]
traj_loc = sys.argv[2]
start = int(sys.argv[3])
end = int(sys.argv[4])
avg_pdb = sys.argv[5]

alignment = 'protein and name CA and (resid 20:25 or resid 50:55 or resid 73:75 or resid 90:94 or resid 112:116 or resid 142:147 or resid 165:169 or resid 190:194 or resid 214:218 or resid 236:240 or resid 253:258 or resid 303:307)'
important = 'protein'

zeros = np.zeros
dot_prod = np.dot
sqrt = np.sqrt
flush = sys.stdout.flush

# ----------------------------------------
# SUBROUTINES:

def ffprint(string):
	print '%s' %(string)
	flush()

# ----------------------------------------
# MAIN PROGRAM:

# INITIATE AND CALCULATE THE IMPORTANT INFORMATION ABOUT THE AVG STRUCTURE
avg = MDAnalysis.Universe(avg_pdb)
avg_all = avg.select_atoms('all')
avg_align = avg.select_atoms(alignment)
avg_important = avg.select_atoms(important)

avg_all.translate(-avg_align.center_of_mass())
pos0 = avg_align.positions

nRes = avg_important.n_residues
avgCoord = zeros((nRes,3),dtype=np.float64)

for i in range(nRes):
	avgCoord[i,:] = avg_important.residues[i].center_of_mass()

# INITIATE AND CREATE THE IMPORTANT ATOM SELECTIONS FOR THE IMPORTANT UNIVERSE
u = MDAnalaysis.Universe(pdb_file)
u_all = u.select_atoms('all')
u_align = u.select_atoms(alignment)
u_important = u.select_atoms(important)

if nRes != len(u_important.residues):
	ffprint('Number of residues do not match between average structure and trajectory universes')
	sys.exit()

# COLLECTING NSTEPS DATA... NEED TO ITERATE THROUGH ALL TRAJECTORIES TO COLLECT THIS...
nSteps = 0
temp = start
while temp <= end:
	u.load_new('%sproduction.%s/production.%s.dcd' %(traj_loc,temp,temp))
	nSteps += len(u.trajectory)
	temp += 1

# ARRAY DECLARATION
allCoord = zeros((nSteps,nRes,3),dtype=np.float64)
cart_covar_array = zeros((3*nRes, 3*nRes),dtype=np.float64)
dist_covar_array = zeros((nRes,nRes),dtype=np.float64)
temp_array = zeros(3*nRes,dtype=np.float64)
msd_array = zeros(nRes,dtype=np.float64)

# TRAJECTORY ANALYSIS; COLLECTING THE COM INFO OF EACH RESIDUE OF INTEREST
temp = 0
while start <= end:
	ffprint('Loading trajectory %s' %(start))
	u.load_new('%sproduction.%s/production.%s.dcd' %(traj_loc,start,start))

	for ts in u.trajectory:
		u_all.translate(-u_align.center_of_mass())
		R,d = rotation_matrix(u_align.positions,pos0)
		u_all.rotate(R)
		for i in range(nRes):
			allCoord[temp,i,:] = u_important.residues[i].center_of_mass()
		temp += 1 
	start += 1

# CALCULATING THE DISTANCE COVAR MATRIX OF RESIDUE RESIDUE PAIRS
for i in range(nSteps):
	for res1 in range(nRes):
		delta_r = allCoord[i,res1,:] - avgCoord[res1,:]		# Calculating the delta r for every timestep
		msd_array[res1] += dot_prod(delta_r,delta_r)
		for res2 in range(res1,nRes):
			dist_covar_array[res1,res2] += dot_prod(allCoord[i,res1,:],allCoord[i,res2,:])
dist_covar_array /= nSteps
msd_array /= nSteps

# COMPLETE THE DISTANCE COVAR MATRIX ANALYSIS BY SUBTRACTING OUT THE MEAN AND NORMALIZING BY THE VARIANCE
for res1 in range(nRes):
	for res2 in range(res1,nRes):
		dist_covar_array[res1,res2] -= dot_prod(avgCoord[res1,:],avgCoord[res2,:])	# Subtracting out the mean positions
		dist_covar_array[res1,res2] /= sqrt(msd_array[res1]*msd_array[res2])	# Normalizing each matrix element by the sqrt of the variance of the positions for res1 and res2
		dist_covar_array[res2,res1] = dist_covar_array[res1,res2]

# CALCULATING THE CARTESIAN COVAR ARRAY OF RESIDUE RESIDUE PAIRS
for i in range(nSteps):
	temp_array = flatten(allCoord[i])
	for res1 in range(3*nRes):
		for res2 in range(res1,3*nRes):
			cart_covar_array[res1,res2] += temp_array[res1]*temp_array[res2]
cart_covar_array /= nSteps

# COMPLETE THE CARTESIAN COVAR MATRIX ANALYSIS BY SUBTRACTING OUT THE MEAN
temp_array = flatten(avgCoord)
for res1 in range(3*nRes):
	for res2 in range(res1,3*nRes):
		covar_array[res1,res2] -= temp_array[res1]*temp_array[res2]
		covar_array[res2,res1] = covar_array[res1,res2]

# OUTPUTING THE COVAR MATRIX
out1 = open('%03d.%03d.dist_cover_matrix.dat' %(sys.argv[3],end),'w')
for i in range(nRes):
	for j in range(nRes):
		out1.write('%.18e ' %(dist_covar_array[i,j]))
	out1.write('\n')
out1.close()

out2 = open('%03d.%03d.cart_cover_matrix.dat' %(sys.argv[3],end),'w')
for i in range(3*nRes):
	for j in range(3*nRes):
		out2.write('%.18e ' %(covar_array[i,j]))
	out2.write('\n')
out2.close()

# WRITE A PCA ANALYSIS OF THIS COVAR ARRAY? 








