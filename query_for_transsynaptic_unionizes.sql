SELECT sp.name AS specimen,
image_series_id,
st.acronym AS structure,
st.graph_order,
h.name AS hemisphere,
psu.is_injection,
psu.projection_volume 
FROM image_series iser 
JOIN specimens sp ON sp.id=iser.specimen_Id 
JOIN projection_structure_unionizes psu ON psu.image_series_id=iser.id 
JOIN hemispheres h ON h.id=psu.hemisphere_id 
JOIN flat_structures_v st ON st.id=psu.structure_id
WHERE psu.image_series_id IN (
  SELECT iser.id 
  FROM image_series iser 
  JOIN projects p on p.id=iser.project_id
  JOIN specimens sp on sp.id=iser.specimen_id 
  JOIN donors d on d.id=sp.donor_id JOIN ages a on a.id=d.age_id
  LEFT JOIN specimens_workflows sw ON sw.specimen_id=sp.id 
  LEFT JOIN workflows w ON w.id=sw.workflow_id
  JOIN run_groups rg on rg.id=iser.run_group_id 
  JOIN runplans rp on rp.id=rg.runplan_id 
  JOIN specimen_blocks sb ON sb.specimen_id=sp.id 
  JOIN blocks b ON b.id=sb.block_id 
  JOIN blocks_section_arrangements bsa ON bsa.block_id=b.id 
  JOIN section_arrangements sa ON sa.id=bsa.section_arrangement_id
WHERE 
iser.id IN (SELECT image_series_id FROM projection_structure_unionizes) AND
p.code IN ('T601','MouseBrainCellAtlasTranssynaptic' ) AND w.name = 'trans-synaptic' --AND iser.id= '1158999274'
AND iser.workflow_state IN ('passed')
) ORDER BY psu.image_series_id, st.graph_order,psu.id;