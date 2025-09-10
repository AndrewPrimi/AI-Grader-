import React from 'react'

function Grader() {
  return (
    <div> 
      <text> Hello Test</text>
    <form action="/submit-notebook/" method="post" >
    <input type="file" name="file" accept=".ipynb"/>
    <button type="submit">Submit Notebook</button>
    </form> 
    </div> 
     
  )
}



export default Grader