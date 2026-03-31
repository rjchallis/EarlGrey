use pyo3::prelude::*;

#[pyfunction]
fn hello(name: &str) -> PyResult<String> {
    Ok(format!("hello {}", name))
}

#[pymodule]
fn earlgrey_bindings(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello, m)?)?;
    Ok(())
}
