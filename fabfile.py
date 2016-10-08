"""
Deployment fabfile for Hoegh Digital
"""
from __future__ import with_statement
from fabric.api import abort, cd, env, lcd, local, require, run, put, settings
from StringIO import StringIO
from os import path

# Module-specific configuration.
PROFILE_NAME = 'someone'
GIT_REPO = 'https://example.com/{name}.git'.format(name=PROFILE_NAME)
DEPLOY_PATH = '/srv/www/sites/example.com/builds'
SITE_PATH = DEPLOY_PATH + '/current/web'
SITE_URL = 'https://example.com/'

scripts = {
    'pre-deploy': ( 'scripts/deploy-clean-files.sh', )
}

env.roledefs = {
    'production': ['exemplaris'],
}
env.user = 'fabric'

# Use the standard .ssh/config files.
env.use_ssh_config = True

# ================== SHARED CODE BELOW THIS LINE ================== #

def _buildpath(tempdir, version):
    return path.join(tempdir, version)

def _composer_install(buildpath):
    with lcd(buildpath):
        local('composer install --prefer-dist --no-dev --no-progress')
        local('composer drupal-scaffold')


def _deploy_dirname(version):
    return version


def _generate_tarball(tempdir, version):
    filename = '{version}.tar.bz2'.format(version=version)
    with lcd(tempdir):
        local('tar cjf {filename} {version}'.format(filename=filename, version=version))

    return filename


def _generate_temporary_folder():
    return local('mktemp -dt {profile}-build'.format(profile=PROFILE_NAME), True)


def _git_clone(buildpath, version):
    local('git clone {repo} {buildpath}'.format(buildpath=buildpath, repo=GIT_REPO))

    with lcd(buildpath):
        local('git checkout {version}'.format(version=version))


def _run_scripts(phase, directory, version):
    with lcd(directory):
        if phase in scripts:
            for script in scripts[phase]:
                local(script)


def _validate_version(version):
    """
    Helper function to validate that a proper version was given.
    """
    version = version.strip()

    return version


def build(version='master'):
    tempdir = _generate_temporary_folder()
    buildpath = _buildpath(tempdir, version)
    _git_clone(buildpath, version)
    _composer_install(buildpath)

    # Run scripts, if any are defined.
    _run_scripts('post-build', buildpath, version)

    print 'Successfully built {profile} in {folder}'.format(folder=buildpath, profile=PROFILE_NAME)

    return tempdir


def deploy(version):
    """
    Deploy a tagged Git version to the server.

    Usage: "fab -R staging deploy:v1.0.0-beta.1".

    This command will make a new checkout of the profile repository, build
    the profile via its make file, replace the previous deployed version
    with the new build, and finally run the post deploy actions, upgrading
    the database, etc.
    """
    require('roles', used_for="configuring what servers to deploy to.")

    version = _validate_version(version)

    if (len(version) < 5):
        abort('Please provide a version to deploy.')

    # Build a copy of the site.
    tempdir = build(version)

    _run_scripts('pre-deploy', _buildpath(tempdir, version), version)

    # Generate a tarball to send to the server.
    tarball = _generate_tarball(tempdir, version)

    with cd(DEPLOY_PATH):
        # If our build folder already exists, remove it first.
        with settings(warn_only=True):
            run('rm -fr {version}'.format(version=version))

        # Copy the build to the server.
        put(path.join(tempdir, tarball), path.join(DEPLOY_PATH, tarball))

        # Uncompress the tarball on the server.
        run('tar xjf {tarball}'.format(tarball=tarball))

        # Remove the tarball, now we're done with it.
        run('rm {tarball}'.format(tarball=tarball))

        # Symlink Drupal site folder and configuration down into our new build.
        run('ln -s ../../../../../site/files {version}/web/sites/default'.format(version=version))
        run('ln -s ../../../../../site/settings.local.php {version}/web/sites/default'.format(version=version))

        # Remove the old "previous" symlink, rename the "current"
        # symlink to "previous".
        with settings(warn_only=True):
            run('rm previous')
            run('mv current previous')

        # Link the new release to "current"
        run('ln -s {version} current'.format(version=version))

    post_deploy(version)

    ## Remove the temporary folder with the make file when we're done.
    local('rm -rf {tempdir}'.format(tempdir=tempdir))


def post_deploy(version=''):
    """
    Run post-deploy operations.

    This includes running database migrations, reverting features, emptying
    the cache and running cron to make sure your Drupal site is coherent.
    """

    # Run database migrationsk
    run('drush -r {site} -l {url} -y updb'.format(site=SITE_PATH, url=SITE_URL))

    # Import new configuration.
    run('drush -r {site} -l {url} -y cim'.format(site=SITE_PATH, url=SITE_URL))

    # Clear the cache.
    run('drush -r {site} -l {url} -y cr'.format(site=SITE_PATH, url=SITE_URL))

    # Run cron for good measure.
    run('drush -r {site} -l {url} -y cron'.format(site=SITE_PATH, url=SITE_URL))


def tag_deploy(tag):
    """
    tag and deploy a new release.
    """
    local('git push')
    local('git tag {tag}'.format(tag=tag))
    local('git push --tag')

    deploy(tag)


def rollback():
    """
    Roll back to the previous version.
    """
    with cd(DEPLOY_PATH):
        # Remove the old "previous" symlink, rename the "current"
        # symlink to "previous".
        with settings(warn_only=True):
            run('rm current')
            run('mv previous current')

    post_deploy()
