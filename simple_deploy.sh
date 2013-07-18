#!/bin/bash
#
# A quick-n-dirty script to copy the project files over to the proper directory 
# (on the local machine) for Apache to serve them, change their ownership and
# set the selinux context so that apache can read them.

DEST=`grep WSGIPythonPath sample_httpd.conf | cut -f2 -d' '`

# Copy all subdirectories, plus manage.py over to the destination directory
# (Nothing else in the top-level directory gets copied)

for i in `ls`
do
	if [ -d $i ]
	then
		cp -av $i $DEST
	fi
done
 
cp manage.py $DEST


# Execute 'manage.py syncdb' to create a new database file
pushd $DEST
/usr/bin/python manage.py syncdb
rm manage.py  # don't need it once the db is created
popd


chown -R apache.apache $DEST
chcon -R unconfined_u:object_r:httpd_sys_content_t:s0 $DEST
