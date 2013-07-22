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
 
# Execute 'manage.py syncdb' to create a new database file
# Note: For reasons that remain unclear, trying to execute
# syncdb in the $DEST dir doesn't work (the db file isn't
# created), so we execute it in the current directory
# and then move it to $DEST
SAVEFILE=sqlite.db.save.`date +%s`
if [ -a sqlite.db ]
then
	mv sqlite.db $SAVEFILE
fi
/usr/bin/python manage.py syncdb
mv sqlite.db $DEST

if [ -a $SAVEFILE ]
then
	mv $SAVEFILE sqlite.db
fi


# Update permissions and selinux context so httpd can access the files
chown -R apache.apache $DEST
chcon -R unconfined_u:object_r:httpd_sys_content_rw_t:s0 $DEST

echo "Don't forget to update the DB path in settings.py!"
