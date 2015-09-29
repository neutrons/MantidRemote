'''
Generates a bash script suitable for calling Mantid python scripts on Fermi.
The script template is below and substitutions for certain things (like the
name of the python script to run) are made before saving the file.  
'''


script_template = '''
#!/usr/bin/bash
#
# Script suitable for calling a python script from within a Mantid-MPI environment
#
# Note: Any string bracketed by 2 'at' signs is a keyword that will be replaced
# with an actual value suitable for the particular job submission.  Nothing
# surrounded by 2 'at' signs should actually show up in this bash script
# once it's written to Fermi.
#

# Set the variables that 'module load mantid-mpi' would normally set
# (Make sure you use the -x param to mpirun to pass the variables that
# the compute nodes need over to them.)
MPI_HOME=/sw/fermi/openmpi-1.8.7_nodlopen
PATH=$MPI_HOME/bin:$PATH
MPI_BIN=$MPI_HOME/bin
MPI_SYSCONFIG=$MPI_HOME/etc
MPI_INCLUDE=$MPI_HOME/include
MPI_LIB=$MPI_HOME/lib

PREFIX=/sw/fermi/mantid-mpi/mantid-mpi-3.4.0-Linux
PATH=$PATH:$PREFIX/bin
# /usr/lib64/openmpi is to pick up boostmpi (not openmpi itself)
LD_LIBRARY_PATH=$PREFIX/lib:$PREFIX/plugins:$MPI_HOME/lib:/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH
PYTHONPATH=$PREFIX/bin:/usr/lib64/openmpi/lib:$PYTHONPATH

# Compute resources
NUM_NODES=@@NUM_NODES@@
CORES_PER_NODE=@@CORES_PER_NODE@@ 
TOTAL_PROCESSES=$((NUM_NODES * CORES_PER_NODE))

# Switch to the transaction directory created for this job
pushd @@TRANSACTION_DIRECTORY@@ > /dev/null

# Kick off python on the computes...
$MPI_BIN/mpirun -n $TOTAL_PROCESSES -x PATH=$PATH -x LD_LIBRARY_PATH=$LD_LIBRARY_PATH -x PYTHONPATH=$PYTHONPATH python ./@@PYTHON_JOB_SCRIPT@@
# We used to have to include  '-npernode $CORES_PER_NODE -hostfile $PBS_NODEFILE', 
# but we don't any more.

# OK, this gets a bit twisted:  we need to set the ACL's on any files that have been written
# so that apache can read (and thus download) them.  Unfortunately, 2 of the files - the
# stdout & stderr files - won't exist until shortly after this script ends. So, what we will
# do is queue up another script in the background (using setsid to detach it from this
# script) that will wait until the stdout/stderr files exist and then run 'setfacl'

ACL_SCRIPT="echo \\"Starting AT script\\";
  while [ -z \\`ls $PBS_JOBID.ER 2>/dev/null\\` ];
  do sleep 1; done;
  while [ -z \\`ls $PBS_JOBID.OU 2>/dev/null\\` ];
  do sleep 1; done;
  for i in \\`find -user $USER\\`;
  do echo \\$i; setfacl -m apache:rw \\$i; done;
  echo \\"Finished AT script\\""

echo $ACL_SCRIPT > adjust_acls.sh
chmod u+x adjust_acls.sh
setsid ./adjust_acls.sh >/dev/null 2>&1 < /dev/null &
# Note: replace the first /dev/null with a filename to see debug output from the ACL script



# Return to the original directory
# (Not sure this is necessary since the process is going to end anyway...)
popd > /dev/null
'''

class ScriptSubstitutionError( Exception):
    '''
    Exception raised when a substitution string in the template above
    is left un-processed.
    '''
    
    
def generate_bash_script( **kwargs):
    '''
    Generates a bash script suitable for calling Mantid python scripts on Fermi.
    The script template is above and substitutions for certain things (like the
    name of the python script to run) are made before saving the file.  

    Returns the template (with substitutions) as a string.
    This is used by the submit view.
    '''
    
    script = script_template
    for arg in kwargs:
        script = script.replace( '@@%s@@'%arg, str(kwargs[arg]))
        
    # Sanity check: make sure we haven't left any un-substituted strings...
    if script.find( '@@') != -1:
        raise ScriptSubstitutionError, 'Failed to provide substitution variable for %s'%script[script.find('@@'):].split()[0]
    
    return script
