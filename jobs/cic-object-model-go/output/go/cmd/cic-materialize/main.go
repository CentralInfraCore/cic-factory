// Command cic-materialize runs the materialization pipeline of SPEC §8 over
// a schema and an authoring input, or the final validation of SPEC §8.7 over
// an already-canonical object.
//
//	cic-materialize -schema schema.yaml -input input.yaml
//	cic-materialize -validate object.yaml
//
// It is also what makes `deadcode ./...` meaningful: without a main package
// every exported symbol is trivially unreachable.
package main

import (
	"errors"
	"flag"
	"fmt"
	"os"

	"github.com/CentralInfraCore/cic-object-model/go/module"
	"github.com/CentralInfraCore/cic-object-model/go/objectmodel"
)

func main() {
	schemaPath := flag.String("schema", "", "path to the CIC schema")
	inputPath := flag.String("input", "", "path to the authoring-plane input")
	validatePath := flag.String("validate", "", "path to a canonical object to validate (SPEC §8.7)")
	deliver := flag.Bool("deliver", false, "hand the result to the module boundary (SPEC §9)")
	flag.Parse()

	if err := run(*schemaPath, *inputPath, *validatePath, *deliver); err != nil {
		var me *objectmodel.Error
		if errors.As(err, &me) {
			fmt.Fprintf(os.Stderr, "error:\n  code: %s\n  invariant: %s\n  stage: %s\n  path: %s\n  detail: %s\n",
				me.Code, me.Invariant, me.Stage, me.Path, me.Detail)
			os.Exit(1)
		}
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

func run(schemaPath, inputPath, validatePath string, deliver bool) error {
	if validatePath != "" {
		object, err := os.ReadFile(validatePath)
		if err != nil {
			return err
		}
		if err := objectmodel.ValidateCanonicalDocument(object); err != nil {
			return err
		}
		fmt.Println("valid")
		return nil
	}

	if schemaPath == "" || inputPath == "" {
		flag.Usage()
		return errors.New("both -schema and -input are required")
	}
	schema, err := os.ReadFile(schemaPath)
	if err != nil {
		return err
	}
	input, err := os.ReadFile(inputPath)
	if err != nil {
		return err
	}

	obj, err := objectmodel.Materialize(schema, input)
	if err != nil {
		return err
	}
	if _, err := os.Stdout.Write(obj.CanonicalYAML()); err != nil {
		return err
	}
	if deliver {
		if err := module.Execute(obj); err != nil {
			return err
		}
		root := obj.Root()
		fmt.Fprintf(os.Stderr, "delivered model %s, root origin %v, path %s\n",
			obj.ModelVersion(), root.Origin(), root.Path())
	}
	return nil
}
