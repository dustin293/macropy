with import <nixpkgs> {};
with pkgs.python36Packages;

stdenv.mkDerivation {
  name = "impurePythonEnv";
  buildInputs = [
    # these packages are required for virtualenv and pip to work:
    #
    python37Full
    python37Packages.virtualenv
    python37Packages.pip
 ];
  src = null;
  shellHook = ''
  # set SOURCE_DATE_EPOCH so that we can use python wheels
  SOURCE_DATE_EPOCH=$(date +%s)
  if ! [ -e  env ]; then
      newenv=1
      python -m venv --system-site-packages --prompt macropy env
  else
      newenv=
  fi
  export PATH=$PWD/env/bin:$PATH
  if ! [ -z $newenv ]; then
      pip install -r requirements.txt
  fi
  if [ "x(raccoon) " != x ] ; then
        PS1="(macropy) $PS1"
  fi
  export PS1
  '';
}
