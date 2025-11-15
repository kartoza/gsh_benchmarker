{
  description = "GeoServer development environment with API testing tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        python-with-packages = pkgs.python3.withPackages (
          p: with p; [
            requests
            pyyaml
            click
            rich
            httpx
            pandas
            matplotlib
            seaborn
            reportlab
          ]
        );

        # Simple wrapper scripts that delegate to Makefile
        test-runner = pkgs.writeShellScriptBin "run-tests" ''
          make test
        '';

        benchmark-runner = pkgs.writeShellScriptBin "run-geoserver-benchmarks" ''
          make benchmark ARGS="$*"
        '';

      in
      {
        # Make scripts available in packages
        packages = {
          inherit test-runner benchmark-runner;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Core development tools
            git
            curl
            jq
            gnumake

            apacheHttpd # HTTP/API testing tools
            httpie
            hurl

            # Benchmarking tools

            # Python environment with GeoServer libraries
            python-with-packages

            orbitron # Java development (for GeoServer Java client)
            openjdk17
            maven

            # Additional useful tools
            tree
            ripgrep
            fd

            # Network debugging
            netcat-openbsd
            nmap

            # JSON/XML processing
            yq-go
            xmlstarlet

            # Documentation and notes
            pandoc

            # Rust toolchain for building ATAC
            cargo
            rustc

            # Beautiful TUI components
            gum

            # Image display in terminal
            chafa

            # Image processing for map previews
            imagemagick

            # Make our custom scripts available
            test-runner
            benchmark-runner
          ];

          shellHook = ''
            echo "🌍 GeospatialHosting Benchmarking Environment"
            echo "================================================"
            echo ""
            echo "Available commands:"
            echo "  • make help - Show all available targets"
            echo "  • make test - Run the test suite"
            echo "  • make benchmark - Run GeoServer benchmarks"
            echo "  • run-tests - Run the test suite (wrapper)"
            echo "  • run-geoserver-benchmarks - Run benchmarks (wrapper)"
            echo "================================================"
          '';
        };
      }
    );
}
